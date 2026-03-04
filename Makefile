CONSTRAINTS := $(shell pwd)/constraints.txt

install-agent-builder:
	cd "CE - Agent Builder" && pip install -c $(CONSTRAINTS) -e ".[dev]"

install-orchestration:
	cd "CE - Multi-Agent Orchestration" && pip install -c $(CONSTRAINTS) -r requirements.txt

install-evals:
	cd "CE - Evals" && pip install -c $(CONSTRAINTS) -e ".[dev]"

install-all: install-agent-builder install-orchestration install-evals
