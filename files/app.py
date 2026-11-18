import hmac
import os
import time

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY", "")
latest = {}  # device_id -> last reading (memory only, lost on restart)


@app.get("/")
def home():
    return send_from_directory(app.root_path, "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/readings")
def add_reading():
    if not API_KEY:
        return {"ok": False, "error": "server has no API_KEY set"}, 500
    sent = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(sent.encode(), API_KEY.encode()):
        return {"ok": False, "error": "bad key"}, 401

    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    temp = data.get("temp")
    hum = data.get("hum")
    rssi = data.get("rssi")

    if not isinstance(device_id, str) or not 0 < len(device_id) <= 64:
        return {"ok": False, "error": "device_id must be text, 1-64 characters"}, 400
    if not isinstance(temp, (int, float)) or not isinstance(hum, (int, float)):
        return {"ok": False, "error": "temp and hum must be numbers"}, 400
    if not -50 <= temp <= 100 or not 0 <= hum <= 100:
        return {"ok": False, "error": "temp or hum out of range"}, 400
    if len(latest) >= 50 and device_id not in latest:
        return {"ok": False, "error": "too many devices"}, 400

    latest[device_id] = {
        "device_id": device_id,
        "temp": round(float(temp), 2),
        "hum": round(float(hum), 2),
        "rssi": rssi if isinstance(rssi, (int, float)) else None,
        "ts": time.time(),
    }
    return {"ok": True}


@app.get("/api/readings")
def list_readings():
    now = time.time()
    rows = []
    for r in latest.values():
        rows.append({**r, "age_s": int(now - r["ts"])})
    rows.sort(key=lambda r: r["device_id"])
    return jsonify(rows)
