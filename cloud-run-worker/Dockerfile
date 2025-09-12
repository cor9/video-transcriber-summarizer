FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 8 app:app
