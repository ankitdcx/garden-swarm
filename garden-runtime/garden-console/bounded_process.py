"""Bounded pipe transport: enforce output caps while a child is running."""
import os
import selectors
import subprocess
import time


def bounded_run(command, input_bytes, *, cwd, env, preexec_fn=None, timeout=60,
                stdout_limit=131072, stderr_limit=16384):
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, cwd=cwd, env=env,
                               preexec_fn=preexec_fn, start_new_session=True)
    output = {"stdout": bytearray(), "stderr": bytearray()}
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    os.set_blocking(process.stdin.fileno(), False)
    selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
    deadline = time.monotonic() + timeout
    sent = 0
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("worker time limit exceeded")
            for key, _ in selector.select(min(remaining, .5)):
                if key.data == "stdin":
                    if sent < len(input_bytes):
                        try:
                            sent += os.write(process.stdin.fileno(), input_bytes[sent:sent + 4096])
                        except BlockingIOError:
                            continue
                        except BrokenPipeError:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                            continue
                    if sent == len(input_bytes):
                        selector.unregister(process.stdin)
                        process.stdin.close()
                    continue
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = output[key.data]
                limit = stdout_limit if key.data == "stdout" else stderr_limit
                if len(target) + len(chunk) > limit:
                    raise ValueError("worker output limit exceeded")
                target.extend(chunk)
        code = process.wait(timeout=max(.01, deadline - time.monotonic()))
        return code, bytes(output["stdout"]), bytes(output["stderr"])
    finally:
        selector.close()
        if process.poll() is None:
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream and not stream.closed:
                stream.close()
