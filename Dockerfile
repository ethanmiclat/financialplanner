# One image, one service: build the React app, then serve it and the API from Flask.
# Works on any container host (Render, Fly.io, Railway). Demo mode is on by default,
# so a public URL gives each visitor a private sandbox and never your own profile.

FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY --from=web /web/dist frontend/dist
ENV FP_DEMO=1 \
    FP_DEMO_DIR=/tmp/footing-demo \
    PYTHONUNBUFFERED=1
EXPOSE 8000
# Threads rather than workers: demo sandboxes are files on local disk, and one
# process keeps a visitor's requests on one disk.
CMD ["sh", "-c", "gunicorn --chdir backend --workers 1 --threads 8 --bind 0.0.0.0:${PORT:-8000} app:app"]
