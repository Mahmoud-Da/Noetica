.PHONY: up down build logs ps restart shell-api shell-frontend

up:
	docker compose up --build

up-d:
	docker compose up --build --detach

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs --follow --tail=100

ps:
	docker compose ps

restart:
	docker compose restart

shell-api:
	docker compose run --rm api sh

shell-frontend:
	docker compose run --rm frontend sh
