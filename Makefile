.PHONY: up down test lint

# PLUMBLINE: two credit unions running the same product with different markup.
up:
	HANDRAIL_ALLOW_FAULTS=1 uv run flask --app "targetapp.app:create_app('quarrybrook')" run --port 8081 &
	HANDRAIL_ALLOW_FAULTS=1 uv run flask --app "targetapp.app:create_app('fernhollow')" run --port 8082 &

down:
	-pkill -f "flask --app targetapp" || true

test:
	uv run ruff check src tests targetapp
	uv run ruff format --check src tests targetapp
	uv run mypy
	uv run pytest -q

lint:
	uv run ruff check --fix src tests targetapp
	uv run ruff format src tests targetapp
