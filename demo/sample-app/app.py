import os
from flask import Flask, jsonify

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise RuntimeError("Missing required environment variable REDIS_URL")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "redis_url_configured": True})


@app.get("/")
def index():
    return jsonify({"service": "checkout-api", "message": "SafeOps demo app is healthy"})
