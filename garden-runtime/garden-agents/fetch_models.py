#!/usr/bin/env python3
"""Operator bootstrap: fetch pinned public models, never run by an agent tool.

No auth tokens, quota evasion, remote shell, or model-supplied download URLs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import os
import urllib.request

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--family", choices=["SmolLM2", "Qwen3", "Qwen3.5", "all"], default="SmolLM2")
    parser.add_argument("--format", choices=["gguf", "onnx"], default="gguf")
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("models.lock.json").read_text())
    destination = Path(args.directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    inventory = manifest["models"]
    if args.format == "onnx":
        if args.family not in {"SmolLM2","Qwen3"}:
            raise ValueError("ONNX bootstrap requires one supported family and separate destination directory")
        wasm = manifest["wasm_qwen_model"] if args.family == "Qwen3" else manifest["wasm_model"]
        inventory = [{**asset, "family":wasm["family"], "model_id":wasm["model_id"], "url":wasm["base_url"]+asset["remote"]} for asset in wasm["assets"]]
    for model in inventory:
        if args.family not in {"all", model["family"]}:
            continue
        target = destination / model["filename"]
        partial = target.with_suffix(".partial")
        hasher = hashlib.sha256()
        size = 0
        try:
            with urllib.request.urlopen(model["url"], timeout=60) as source, partial.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 2 * 1024 ** 3:
                        raise ValueError("model download exceeds bootstrap size budget")
                    hasher.update(chunk)
                    output.write(chunk)
            if hasher.hexdigest() != model["sha256"]:
                raise ValueError("model hash mismatch; refusing installation")
            os.chmod(partial, 0o444)
            partial.replace(target)
            print(json.dumps({"model": model["model_id"], "path": str(target), "bytes": size, "sha256": hasher.hexdigest(), "status": "EXPERIMENTAL"}))
        finally:
            partial.unlink(missing_ok=True)

if __name__ == "__main__":
    main()
