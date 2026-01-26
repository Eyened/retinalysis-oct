# Docker Setup for OCT Analysis Worker

This guide explains how to run the OCT analysis Celery worker using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- **RabbitMQ running on the host system**

## Quick Start

### Development Setup

1. **Ensure RabbitMQ is running on the host:**
   ```bash
   # Check RabbitMQ status
   sudo systemctl status rabbitmq-server  # Linux
   # or
   brew services list | grep rabbitmq  # macOS
   ```

2. **Start worker:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f worker
   ```

4. **Stop worker:**
   ```bash
   docker-compose down
   ```

## Services

### Worker
- **Image**: Built from `Dockerfile`
- **Purpose**: Celery worker for OCT analysis
- **Concurrency**: 2 workers (configurable)
- **Broker**: Connects to RabbitMQ on host via `host.docker.internal`
- **Volumes**:
  - `./output:/app/output` - Output directory for reports
  - `./data:/app/data:ro` - Input data directory (read-only)

## Configuration

### Environment Variables

Set environment variables in `docker-compose.yml` or use a `.env` file:

```bash
# .env
CELERY_BROKER_URL=amqp://guest:guest@host.docker.internal:5672//
CELERY_RESULT_BACKEND=rpc://
OCT_WORKER_OUTPUT_DIR=/app/output
OCT_TASK_TIME_LIMIT=3600
OCT_WORKER_LOG_LEVEL=INFO
```

**Note**: When running in Docker, use `host.docker.internal` to connect to RabbitMQ on the host. On Linux, you may need to use `--network=host` or ensure `host.docker.internal` is available.

### Volume Mounts

Create directories for data and output:

```bash
mkdir -p data output
```

- **`./data`**: Place input OCT files and segmentations here
- **`./output`**: Generated reports will be saved here

## Production Setup

For production, ensure RabbitMQ is properly configured with authentication and use secure connection strings:

```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with secure RabbitMQ credentials

# Start worker
docker-compose up -d
```

### Production Environment Variables

Create a `.env` file with secure values:

```bash
# RabbitMQ connection (use actual credentials)
CELERY_BROKER_URL=amqp://username:password@host.docker.internal:5672/vhost
CELERY_RESULT_BACKEND=rpc://

WORKER_CONCURRENCY=2
WORKER_REPLICAS=2
TASK_TIME_LIMIT=3600
LOG_LEVEL=INFO
```

## Building Images

### Standard Build

```bash
docker build -t rtnls-oct-worker .
```

### With eyened Support

```bash
docker build --build-arg EXTRA_DEPS="worker,eyened" -t rtnls-oct-worker:eyened .
```

### With Monitoring

```bash
docker build --build-arg EXTRA_DEPS="worker,monitoring" -t rtnls-oct-worker:monitoring .
```

## Usage Examples

### Submitting Tasks

From a Python script on the host:

```python
from worker.tasks import analyze_oct_thickness

# Note: Use paths relative to the mounted volume
task = analyze_oct_thickness.delay(
    oct_volume_path='/app/data/oct.dcm',  # Path inside container
    segmentation_path='/app/data/segmentation.npz',
    laterality='R',
    thickness_maps={'RNFL': {'top': 'ILM', 'bottom': 'RNFL'}},
    output_dir='/app/output',
    report_id='test_001'
)

result = task.get()
```

### Accessing Results

Results are saved to `./output` on the host:

```bash
ls -la output/
# report.html
# oct_image.png
# RNFL.png
# ...
```

## Troubleshooting

### Check Service Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs worker
docker-compose logs redis

# Follow logs
docker-compose logs -f worker
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart worker
```

### Clean Up

```bash
# Stop and remove containers
docker-compose down

# Stop, remove containers and volumes
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Worker Not Processing Tasks

1. Check RabbitMQ connection:
   ```bash
   docker-compose exec worker celery -A worker.celery_app inspect ping
   ```

2. Verify RabbitMQ is running on host:
   ```bash
   # Check RabbitMQ status
   sudo systemctl status rabbitmq-server  # Linux
   # or
   brew services list | grep rabbitmq  # macOS
   ```

3. Check registered tasks:
   ```bash
   docker-compose exec worker celery -A worker.celery_app inspect registered
   ```

4. Check active tasks:
   ```bash
   docker-compose exec worker celery -A worker.celery_app inspect active
   ```

5. Test RabbitMQ connection from container:
   ```bash
   docker-compose exec worker python -c "from kombu import Connection; conn = Connection('amqp://guest:guest@host.docker.internal:5672//'); conn.connect(); print('Connected!'); conn.close()"
   ```

### Permission Issues

If you encounter permission issues with volumes:

```bash
# Fix output directory permissions
sudo chown -R $USER:$USER output/
chmod -R 755 output/
```

### Memory Issues

If workers run out of memory:

1. Reduce concurrency in `docker-compose.yml`:
   ```yaml
   command: celery -A worker.celery_app worker --loglevel=info --concurrency=1
   ```

2. Reduce worker replicas in production:
   ```bash
   WORKER_REPLICAS=1 docker-compose -f docker-compose.prod.yml up -d
   ```

## Networking

The worker connects to RabbitMQ on the host system using `host.docker.internal`. This allows the containerized worker to communicate with RabbitMQ running on the host machine.

**Linux Note**: On Linux, `host.docker.internal` may not be available by default. You can either:
- Use `--network=host` mode (less secure)
- Add `--add-host=host.docker.internal:host-gateway` to docker-compose.yml
- Use the host's IP address directly

## Scaling Workers

### Development

Edit `docker-compose.yml`:

```yaml
worker:
  command: celery -A worker.celery_app worker --loglevel=info --concurrency=4
```

### Production

Scale manually:

```bash
docker-compose up -d --scale worker=4
```

## Monitoring

### Command Line Monitoring

```bash
# Inspect workers
docker-compose exec worker celery -A worker.celery_app inspect active

# Get worker stats
docker-compose exec worker celery -A worker.celery_app inspect stats

# List registered tasks
docker-compose exec worker celery -A worker.celery_app inspect registered
```

## Security Considerations

### Production Checklist

- [ ] Configure RabbitMQ with proper authentication
- [ ] Use secure connection strings (avoid default guest/guest)
- [ ] Set appropriate resource limits
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity
- [ ] Use SSL/TLS for RabbitMQ connections if needed

## Backup

### Output Reports

Reports are stored in `./output` on the host. Backup this directory regularly.

