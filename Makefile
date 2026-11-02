.PHONY: up down logs migrate migrations superuser seed shell test lint format

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f web

migrate:
	docker compose exec web python manage.py migrate

migrations:
	docker compose exec web python manage.py makemigrations

superuser:
	docker compose exec web python manage.py createsuperuser

seed:
	docker compose exec web python manage.py seed_demo

shell:
	docker compose exec web python manage.py shell

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .
