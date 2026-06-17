# KOSMO Local Docker Stack

This stack runs the full local development environment:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- Postgres: localhost:5432
- MongoDB: localhost:27017
- Redis: localhost:6379

## Start

```bash
docker compose up --build
```

The backend container automatically:

- generates a local-only RS256 JWT key pair under `/tmp/kosmo-secrets`
- applies Alembic migrations with `alembic upgrade head`
- starts FastAPI with Uvicorn

## Optional Overrides

Copy `.env.example` to `.env` only when you need to change ports, passwords, or app settings:

```bash
cp .env.example .env
```

The committed defaults are enough for normal local development.

## Useful Commands

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend alembic upgrade head
docker compose exec backend python -m kosmo.infrastructure.scripts.seed_dev_user
```

## Reset Local Data

This deletes Postgres, MongoDB, Redis, and frontend cache volumes:

```bash
docker compose down -v
```

Then start again:

```bash
docker compose up --build
```

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/openapi.json
```
