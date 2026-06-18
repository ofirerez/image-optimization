# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Flask web app for image optimization. Users upload JPEG, PNG, or WebP images via drag-and-drop and see a before/after comparison. SVG and GIF are explicitly rejected. OpenCV is available as a dependency for future processing features but not yet used.

## Running locally

```bash
cd image_optimization
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
FLASK_ENV=development python wsgi.py    # Dev server on :5050
```

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
python -m pytest tests/test_upload.py -k test_reject_gif   # Single test
```

## Docker (production)

```bash
docker build -f deploy/Dockerfile -t image-optimizer .
docker run -p 8000:8000 image-optimizer
```

Uses Gunicorn with 4 workers on port 8000.

## Project structure

```
├── src/image_optimizer/       # Application package
│   ├── __init__.py            # App factory, Flask-Limiter init, atexit cleanup
│   ├── routes.py              # / (UI), /api/upload (POST), /uploads/<file> (serve)
│   └── templates/index.html   # SPA frontend (vanilla JS, no build step)
├── config/settings.py         # Dev/prod configs, upload limits, allowed extensions
├── deploy/Dockerfile          # Production container
├── tests/                     # pytest suite
├── wsgi.py                    # Entrypoint (dev + gunicorn target: wsgi:app)
└── requirements.txt
```

## Rules

- Always ask for explicit user permission before pushing to any remote (git push, gh pr create, etc.)

## Key conventions

- App factory pattern: `src.image_optimizer.create_app()`
- WSGI entrypoint: `wsgi:app`
- Rate limiting: 30 requests/min per IP via Flask-Limiter (in-memory storage for dev; configure Redis for production)
- Max upload: 25 MB (set in `Config.MAX_CONTENT_LENGTH`)
- Uploads go to `/tmp/image_optimizer`; old files cleaned up in a background thread, full folder wiped on process exit via `atexit`
- File validation: extension check + Pillow `Image.verify()` to reject corrupted files
- Port 5050 for local dev (5000 is typically taken by macOS AirPlay)
