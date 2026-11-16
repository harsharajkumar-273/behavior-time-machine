FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim-bookworm
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home app
COPY backend/ backend/
COPY --from=frontend /build/dist/ frontend/dist/
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
