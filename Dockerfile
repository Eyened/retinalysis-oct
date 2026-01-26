FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY . .

# Install the package with worker dependencies
# Use build arg to optionally include eyened support
ARG EXTRA_DEPS=worker
RUN pip install --no-cache-dir -e ".[${EXTRA_DEPS}]"

RUN git clone -b development https://github.com/Eyened/eyened-platform.git
RUN cd eyened-platform/orm && pip install .

# Set Python path
ENV PYTHONPATH=/app

WORKDIR /app/worker

# Default command (can be overridden in docker-compose)
ENTRYPOINT celery -A tasks worker --loglevel=INFO -P threads -Q rtnls-oct -c 4


