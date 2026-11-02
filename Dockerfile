# API-only backend for Cloud Run (api.py). The UI is web/ on Vercel; the Streamlit dashboard (app.py), the
# testnet / on-chain scripts and the eval tooling are not in the image (see .dockerignore, an allowlist).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 GATEWAY_LOG=

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8080
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8080}"]
