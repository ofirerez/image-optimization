# Image Optimizer

A Flask web app for image optimization. Upload JPEG, PNG, or WebP images via drag-and-drop, adjust compression settings, and download optimized versions with a before/after comparison.

## Features

- Drag-and-drop image upload (JPEG, PNG, WebP)
- Three optimization presets: **Aggressive**, **Balanced**, **Lossless**
- Adjustable quality and resize controls
- Optional metadata stripping
- Before/after comparison with file size savings
- EXIF metadata viewer
- Rate limiting (30 req/min per IP)
- Automatic cleanup of temporary uploads

## Quick Start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
FLASK_ENV=development python wsgi.py
```

The app runs on **http://localhost:5050**.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Web UI |
| POST | `/api/upload` | Upload an image (multipart, field: `file`) |
| POST | `/api/optimize` | Optimize an uploaded image (JSON body) |
| GET | `/api/metadata/<filename>` | Get image metadata and EXIF info |
| GET | `/api/download/<filename>` | Download an optimized image |
| GET | `/uploads/<filename>` | Serve an uploaded/optimized file |

### Optimize request body

```json
{
  "filename": "abc123.jpg",
  "quality": 80,
  "resize_percent": 100,
  "strip_metadata": true,
  "preset": "balanced"
}
```

Presets: `aggressive` (quality 60), `balanced` (quality 80), `lossless` (quality 95).

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | `development` enables debug mode |
| `SECRET_KEY` | `dev-secret-change-me` | Flask secret key |
| `UPLOAD_FOLDER` | `/tmp/image_optimizer` | Temporary upload directory |
| `CLEANUP_MAX_AGE` | `3600` | Seconds before uploaded files are cleaned up |

Max upload size is 25 MB.

## Deployment

### Docker

```bash
docker build -f deploy/Dockerfile -t image-optimizer .
docker run -p 8000:8000 image-optimizer
```

This runs Gunicorn with 4 workers on port 8000.

### Docker Compose

```yaml
services:
  image-optimizer:
    build:
      context: .
      dockerfile: deploy/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-production-secret
    restart: unless-stopped
```

### Manual deployment

1. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/ofirerez/image-optimization.git
   cd image-optimization
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run with Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app
   ```

3. Put behind a reverse proxy (Nginx/Caddy) for TLS and static file serving.

### Production checklist

- Set `SECRET_KEY` to a strong random value
- Configure a reverse proxy (Nginx, Caddy) with TLS
- For multi-instance deployments, switch Flask-Limiter to Redis storage
- Mount a persistent volume for `UPLOAD_FOLDER` if you need uploads to survive restarts
- System dependencies required: `libgl1`, `libglib2.0-0` (included in the Docker image)

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

## Tech Stack

- **Backend:** Flask, Pillow, OpenCV (available for future features), Gunicorn
- **Frontend:** Vanilla JS (no build step)
- **Rate limiting:** Flask-Limiter (in-memory; Redis for production)
