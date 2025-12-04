.PHONY: docker docker-stop dev migrate

# Start PostgreSQL container
docker:
	docker run -d \
		--name agentbeats-postgres \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_DB=agentbeats \
		-p 5432:5432 \
		postgres:16-alpine

# Stop and remove PostgreSQL container
docker-stop:
	docker stop agentbeats-postgres && docker rm agentbeats-postgres

# Run the app in development mode
dev:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run migrations only
migrate:
	uv run python -c "import asyncio; from db import init_db; asyncio.run(init_db())"
