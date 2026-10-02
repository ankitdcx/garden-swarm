SHELL := /bin/bash
CARGO ?= cargo
PYTHON ?= python3

.PHONY: build test bench formal console
build:
	$(CARGO) build --release --locked --manifest-path garden-kernel/Cargo.toml
test:
	$(CARGO) test --locked --manifest-path garden-kernel/Cargo.toml
	PYTHONPATH=garden-lang:garden-agents $(PYTHON) -m unittest discover -s garden-tests -p 'test_*.py' -v
bench:
	$(PYTHON) gardenbench/run.py --binary garden-kernel/target/release/garden-gate
formal:
	$(PYTHON) garden-tests/formal_model.py
console:
	$(PYTHON) garden-console/server.py
