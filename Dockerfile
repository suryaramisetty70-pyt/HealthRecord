FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py index.html ./
RUN mkdir /data && useradd -m appuser && chown appuser /data
USER appuser
ENV DATABASE_PATH=/data/health.db
ENV SECURE_COOKIE=1
EXPOSE 10000
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
