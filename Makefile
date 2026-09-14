.PHONY: help install clean test test-fast test-contract test-machine test-optional test-full test-lanes health render

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

help:
	@echo "Comandos FLUJO:"
	@echo "  make install      Instalar dependencias"
	@echo "  make health       Comprobar estructura y archivos"
	@echo "  make test         Ejecutar la suite FLUJO"
	@echo "  make test-fast    Ejecutar candidatos pequenos"
	@echo "  make test-contract Ejecutar contratos"
	@echo "  make test-full    Ejecutar todas las pruebas FLUJO"
	@echo "  make test-lanes   Mostrar clasificacion de pruebas"
	@echo "  make clean        Limpiar caches y salidas locales"

install:
	bash scripts/setup.sh

health:
	$(PYTHON) scripts/flujo_health.py

clean:
	bash scripts/limpiar_basura.sh

test:
	PYTHONPATH=src $(PYTHON) -m pytest -o addopts='' -m flujo -q

test-fast:
	PYTHONPATH=src $(PYTHON) -m pytest -m 'flujo and lane_fast' -q

test-contract:
	PYTHONPATH=src $(PYTHON) -m pytest -m 'flujo and lane_contract' -q

test-machine:
	PYTHONPATH=src $(PYTHON) -m pytest -m 'flujo and lane_machine' -q

test-optional:
	PYTHONPATH=src $(PYTHON) -m pytest -m 'flujo and lane_optional' -q

test-full:
	PYTHONPATH=src $(PYTHON) -m pytest -o addopts='' -m flujo -q

test-lanes:
	$(PYTHON) tools/test_lane_map.py --format text

render:
	PYTHONPATH=src $(PYTHON) scripts/piezas_check_outputs.py
