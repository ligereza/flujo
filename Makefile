.PHONY: help install health clean test

PYTHON := python3

help:
	@echo "Comandos disponibles:"
	@echo "  make install    Instalar dependencias"
	@echo "  make health     Ejecutar health check"
	@echo "  make clean      Limpiar outputs generados"
	@echo "  make test       Ejecutar tests mínimos"
	@echo "  make render     Generar piezas vectoriales de ejemplo"

install:
	$(PYTHON) -m pip install -r requirements.txt

health: clean
	$(PYTHON) scripts/flujo_health.py

clean:
	$(PYTHON) scripts/flujo_clean_generated.py

test:
	$(PYTHON) -m pytest tests/ -q

render:
	$(PYTHON) scripts/piezas_generar.py projects/piezas_vectoriales/etiquetas_ejemplo/config.json

new-flyer:
	$(PYTHON) scripts/flyer_create_project.py "$(NAME)"
