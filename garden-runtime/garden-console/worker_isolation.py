"""Linux inference jail: read-only code/model, private filesystem, no sockets.

Uses chroot only when the host grants it, then drops all UID privileges and adds
a seccomp network/ptrace deny filter. Failure leaves inference unavailable.
This is defense in depth, not a proof against host/kernel compromise.
"""
import ctypes
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import tempfile


class IsolationUnavailable(RuntimeError):
    pass


class Filter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]


class Program(ctypes.Structure):
    _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]


LIBC = ctypes.CDLL(None, use_errno=True)
# x86_64 syscalls: sockets, ptrace and cross-process memory operations.
NETWORK_AND_PTRACE = [41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 101, 288, 299, 307, 310, 311]
instructions = [Filter(0x20, 0, 0, 4), Filter(0x15, 1, 0, 0xC000003E),
                Filter(0x06, 0, 0, 0x80000000), Filter(0x20, 0, 0, 0)]
for number in NETWORK_AND_PTRACE:
    instructions.extend([Filter(0x15, 0, 1, number), Filter(0x06, 0, 0, 0x00050000 | 1)])
instructions.append(Filter(0x06, 0, 0, 0x7FFF0000))
FILTERS = (Filter * len(instructions))(*instructions)
PROGRAM = Program(len(instructions), FILTERS)


def _copy(source: Path, jail: Path, destination: str | None = None):
    target = jail / (destination or str(source)).lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    shutil.copy2(source.resolve(), target)
    target.chmod(target.stat().st_mode & ~0o222)


def _libraries(binary: Path, jail: Path):
    result = subprocess.run(["ldd", str(binary)], capture_output=True, text=True, timeout=5)
    for match in re.findall(r"(?:=>\s*)?(/[^\s()]+)", result.stdout):
        library = Path(match)
        if library.is_file(): _copy(library, jail)


class WorkerJail:
    def __init__(self, agents: Path, *, binary: Path | None = None, model: Path | None = None):
        if os.geteuid() != 0 or platform.system() != "Linux" or platform.machine() != "x86_64":
            raise IsolationUnavailable("inference jail needs Linux x86_64 chroot authority")
        self.path = Path(tempfile.mkdtemp(prefix="garden-worker-jail-"))
        self.path.chmod(0o755)
        try:
            interpreter = Path("/usr/bin/python3")
            if not interpreter.is_file(): raise IsolationUnavailable("system Python missing")
            config = subprocess.run([str(interpreter), "-c", "import sysconfig;print(sysconfig.get_path('stdlib'))"],
                                    capture_output=True, text=True, timeout=5, check=True)
            stdlib = Path(config.stdout.strip())
            _copy(interpreter, self.path)
            _libraries(interpreter, self.path)
            shutil.copytree(stdlib, self.path / str(stdlib).lstrip("/"),
                            ignore=shutil.ignore_patterns("__pycache__", "site-packages", "dist-packages", "test", "tests"))
            for extension in stdlib.rglob("*.so"): _libraries(extension, self.path)
            shutil.copytree(agents, self.path / "app", ignore=shutil.ignore_patterns("__pycache__"))
            for file in (self.path / "app").rglob("*"):
                if file.is_file(): file.chmod(file.stat().st_mode & ~0o222)
            (self.path / "tmp").mkdir(mode=0o1777)
            (self.path / "tmp").chmod(0o1777)
            (self.path / "dev").mkdir()
            (self.path / "dev/null").touch(mode=0o666)
            (self.path / "dev/null").chmod(0o666)
            self.env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"}
            if binary and model:
                _copy(binary, self.path, "/inference/" + binary.name)
                _libraries(binary, self.path)
                for library in binary.parent.glob("*.so*"):
                    if library.is_file():
                        _copy(library, self.path, "/inference/" + library.name)
                        _libraries(library, self.path)
                _copy(model, self.path, "/models/model.gguf")
                self.env.update(GARDEN_LLAMA_BINARY="/inference/" + binary.name, GARDEN_MODEL_PATH="/models/model.gguf")
        except Exception:
            self.close()
            raise

    def enter(self):
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
        os.chroot(self.path)
        os.chdir("/app")
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)
        if LIBC.prctl(38, 1, 0, 0, 0) != 0 or LIBC.prctl(22, 2, ctypes.byref(PROGRAM), 0, 0) != 0:
            os._exit(126)

    def close(self):
        shutil.rmtree(self.path, ignore_errors=True)
