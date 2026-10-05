"""Gunicorn config: uvicorn workers, sized from env."""

import os

bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"  # noqa: S104
workers = int(os.getenv("WORKERS", "4"))
worker_class = "uvicorn_worker.UvicornWorker"
timeout = 60
graceful_timeout = 30
keepalive = 5
max_requests = 10000
max_requests_jitter = 1000
accesslog = None  # access logging is done by the app (structured, with request IDs)
