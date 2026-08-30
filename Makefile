# Prérequis : uv (https://docs.astral.sh/uv/)
UV ?= uv

setup:
	$(UV) sync --locked --all-extras

test:             ## 33 tests fermés, sans réseau
	$(UV) run pytest

lint:
	$(UV) run ruff check .

data:             ## les quatre fichiers publics, environ 11 Mo (réseau requis)
	$(UV) run scc fetch

verify:           ## les constantes du dépôt contre le classeur du BSIF
	$(UV) run scc verifier

all: data verify  ## tout : données, vérification, calculs et figures
	$(UV) run scc tout
