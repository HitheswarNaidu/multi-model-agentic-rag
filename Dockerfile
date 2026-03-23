# Base Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8000/api/status || exit 1

# Run FastAPI backend
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
