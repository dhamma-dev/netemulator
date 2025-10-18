.PHONY: help install start stop clean test lint format

help:
	@echo "NetEmulator - Makefile targets:"
	@echo ""
	@echo "  install    - Install dependencies"
	@echo "  start      - Start NetEmulator services"
	@echo "  stop       - Stop NetEmulator services"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linters"
	@echo "  format     - Format code with black"
	@echo "  clean      - Clean up generated files"
	@echo "  deploy     - Deploy example topology"
	@echo ""

install:
	@echo "Installing dependencies..."
	@sudo scripts/install_dependencies.sh

start:
	@echo "Starting services..."
	@scripts/start_services.sh

stop:
	@echo "Stopping services..."
	@scripts/stop_services.sh

test:
	@echo "Running tests..."
	@source venv/bin/activate && pytest tests/ -v

lint:
	@echo "Running linters..."
	@source venv/bin/activate && pylint netemulator/
	@source venv/bin/activate && mypy netemulator/

format:
	@echo "Formatting code..."
	@source venv/bin/activate && black netemulator/ tests/

clean:
	@echo "Cleaning up..."
	@sudo mn -c 2>/dev/null || true
	@rm -rf logs/*.log logs/*.pid
	@rm -rf __pycache__ */__pycache__ */*/__pycache__
	@rm -rf .pytest_cache
	@rm -rf build/ dist/ *.egg-info
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete

deploy:
	@echo "Deploying example topology..."
	@scripts/deploy_topology.sh examples/dual_isp_topology.yaml

