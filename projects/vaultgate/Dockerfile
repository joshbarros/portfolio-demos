FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
COPY --from=web /web/dist ./frontend/dist
EXPOSE 8099
CMD ["sh", "-c", "python -m vaultgate.init_db && uvicorn vaultgate.app:app --host 0.0.0.0 --port 8099"]
