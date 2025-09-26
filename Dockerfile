FROM python:3.11-slim

# Keep Python output unbuffered and avoid .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed to build some Python packages and to allow psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /app/

# Install Python deps; ensure uvicorn and a binary-friendly psycopg2 are available
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard] psycopg2-binary

# Copy project
COPY . /app

# Expose the FastAPI default port
EXPOSE 8000

# Use uvicorn to serve the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
