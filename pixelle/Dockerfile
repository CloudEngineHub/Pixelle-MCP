# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Use uv to install dependencies
RUN uv sync --frozen --no-cache

# Ensure using Python in virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 9002

# Start command
CMD ["python", "main.py"] 