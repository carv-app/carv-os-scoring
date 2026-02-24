FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ src/

USER appuser

EXPOSE 8080

CMD ["uvicorn", "scoring.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
