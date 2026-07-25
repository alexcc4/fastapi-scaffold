import os


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "app.uvicorn_worker.AppUvicornWorker"

accesslog = None
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
capture_output = False
preload_app = False
