from flask import Flask, jsonify, request
import time
import random
from threading import Lock
from datetime import datetime, timedelta

app = Flask(__name__)

stock_lock = Lock()
cache = {"platters": {}, "timestamp": None, "ttl": 5}

platters = {
    1: {"stock": 45, "max_stock": 120, "prep_time": 5, "popular": False},
    2: {"stock": 30, "max_stock": 80, "prep_time": 8, "popular": False},
    3: {"stock": 15, "max_stock": 50, "prep_time": 10, "popular": False}
}

plates = 120
processed_orders = set()
total_requests = 0
failure_count = 0

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def get_cached_platter(platter_id):
    if cache["timestamp"] and datetime.now() - cache["timestamp"] < timedelta(seconds=cache["ttl"]):
        if platter_id in cache["platters"]:
            return cache["platters"][platter_id]
    with stock_lock:
        if platter_id in platters:
            cache["platters"][platter_id] = platters[platter_id].copy()
            cache["timestamp"] = datetime.now()
            return cache["platters"][platter_id]
    return None

def invalidate_cache():
    cache["timestamp"] = None
    cache["platters"] = {}

@app.route("/platter/<int:platter_id>", methods=["GET", "OPTIONS"])
def get_platter(platter_id):
    global total_requests
    total_requests += 1
    if request.method == "OPTIONS":
        return jsonify({}), 200
    cached = get_cached_platter(platter_id)
    if cached:
        return jsonify({**cached, "cached": True})
    return jsonify({"error": "Not found"}), 404

@app.route("/platter/<int:platter_id>/deduct", methods=["POST", "OPTIONS"])
def deduct_stock(platter_id):
    global total_requests, failure_count, plates
    total_requests += 1
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    order_id = data.get("order_id")
    quantity = data.get("quantity", 1)
    if order_id and order_id in processed_orders:
        return jsonify({"error": "Order already processed", "idempotent": True}), 409
    with stock_lock:
        if platter_id not in platters:
            failure_count += 1
            return jsonify({"error": "Platter not found"}), 404
        if platters[platter_id]["stock"] < quantity:
            failure_count += 1
            return jsonify({"error": "Insufficient stock"}), 400
        platters[platter_id]["stock"] -= quantity
        plates -= quantity
        if order_id:
            processed_orders.add(order_id)
        invalidate_cache()
        return jsonify({"success": True, "remaining_stock": platters[platter_id]["stock"]})

@app.route("/plates", methods=["GET", "OPTIONS"])
def get_plates():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    return jsonify({"plates": plates})

@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    invalidate_cache()
    return jsonify({"status": "Cache cleared"})

@app.route("/metrics", methods=["GET"])
def metrics():
    with stock_lock:
        return jsonify({
            "service": "stock", "total_requests": total_requests,
            "failure_count": failure_count, "plates_left": plates,
            "total_items": sum(p["stock"] for p in platters.values()),
            "processed_orders": len(processed_orders)
        })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "stock", "status": "online", "time": time.time()})

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 STOCK SERVICE RUNNING")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5004, debug=True, threaded=True)