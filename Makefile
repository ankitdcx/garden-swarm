.PHONY: test prototype-test server-test swarm-test adversarial gate server

PYTHON ?= python

prototype-test:
	$(PYTHON) -m pytest -q prototype/tests

server-test:
	$(PYTHON) -m pytest -q server/tests

swarm-test:
	$(PYTHON) -m unittest discover -s swarm/tests -v

adversarial:
	$(PYTHON) -m pytest -q tests/adversarial

test: prototype-test server-test swarm-test adversarial

gate:
	$(PYTHON) -m prototype.actiongate

server:
	uvicorn server.app:app --host 127.0.0.1 --port 8000
