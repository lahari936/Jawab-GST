# Build from the repo root so the synthetic samples ship with the image:
#   docker build -f backend/Dockerfile -t jawab-api .
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY samples/jawab ./samples/jawab
ENV SAMPLES_DIR=/app/samples/jawab PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
