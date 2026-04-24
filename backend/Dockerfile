FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv pip install --system -e .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "kosmo.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]