# Makefile for Voltcast-AI Load Forecasting

.PHONY: help install test seed verify up down clean

help:
	@echo "Voltcast-AI Load Forecasting - Available Commands"
	@echo "=================================================="
	@echo "install     - Install Python dependencies"
	@echo "test        - Run all tests"
	@echo "seed        - Seed database with historical data"
	@echo "verify      - Verify Phase 2 setup"
	@echo "up          - Start all services with Docker Compose"
	@echo "down        - Stop all services"
	@echo "clean       - Clean up temporary files"
	@echo "run         - Run API locally (without Docker)"

install:
	pip install -r req.txt

test:
	pytest tests/ -v

seed:
	python scripts/seed_hourly_actuals.py hourly_data(2000-2023).csv

verify:
	python verify_phase2.py

up:
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo "Services started! API available at http://localhost:8000"

down:
	docker-compose down

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage 2>/dev/null || true

run:
	python run_api.py
