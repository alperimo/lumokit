DOCKER_CMD ?= docker

###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###

dev:
	cd ./src && uvicorn main:app --reload

setup:
	cd ./ && poetry install
	cd ./ && poetry run pre-commit install

###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###
###/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\/\###

## DOCKER COMMANDS - START ##

build:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml build

up:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml up -d

restart:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml restart

logs:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml logs -f

down:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml down

clean:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml down -v --remove-orphans && docker system prune -f

logs-backend:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml logs -f backend

logs-postgres:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml logs -f postgres

logs-nginx:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml logs -f nginx

manage:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml exec backend bash

migrations:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml exec backend alembic -c alembic.ini revision --autogenerate -m "$(MSG)"

migrate:
	$(DOCKER_CMD) compose -f docker-compose.prod.yml exec backend alembic -c alembic.ini upgrade head

## DOCKER COMMANDS - END ##