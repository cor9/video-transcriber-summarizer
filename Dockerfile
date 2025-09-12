FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    yt-dlp==2024.08.06 \
    youtube-transcript-api==0.6.2 \
    google-generativeai>=0.7.2 \
    flask==3.0.3 \
    google-cloud-pubsub==2.21.6 \
    google-cloud-storage==2.17.0 \
    google-cloud-firestore==2.16.0 \
    httpx==0.27.2 \
    werkzeug==3.0.3

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Create directories for transcripts and summaries
RUN mkdir -p transcripts summaries

# Set environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "cloud_run_app.py"]
