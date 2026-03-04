from flask import Flask, request, jsonify
import threading
import time
import requests
from datetime import datetime
from collections import deque
import uuid

app = Flask(__name__)

orders = {}
processed_order_ids = set()
request_timestamps = deque(maxlen=60)

metrics = {
    "total_requests": 0, "failures": 0, "timeouts": 0,
    "completed": 0, "active_orders": 0, "total_orders": 0,
    "latencies": deque(maxlen=100)
}

STOCK_SERVICE = "http://127.0.0.1:5004"
KITCHEN_SERVICE = "http://127.0.0.1:5003"

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def process_order_async(oid, platter_id, student_id):
    stages = [
        {"status": "Pending", "duration": 2},
        {"status": "Stock Verified", "duration": 3},
        {"status": "In Kitchen", "duration": 5},
        {"status": "Ready", "duration": 0}
    ]
    try:
        for stage in stages:
            if oid not in orders: break
            orders[oid]["status"] = stage["status"]
            orders[oid]["updated_at"] = datetime.now().isoformat()
            if stage["status"] == "Stock Verified":
                try:
                    response = requests.post(f"{STOCK_SERVICE}/platter/{platter_id}/deduct",
                        json={"order_id": oid, "quantity": 1, "idempotency_key": str(uuid.uuid4())}, timeout=5)
                    if response.status_code != 200:
                        orders[oid]["status"] = "Failed - Stock Issue"
                        metrics["failures"] += 1
                        metrics["active_orders"] = max(0, metrics["active_orders"] - 1)
                        return
                except Exception as e:
                    orders[oid]["status"] = "Failed"
                    orders[oid]["error"] = str(e)
                    metrics["failures"] += 1
                    metrics["active_orders"] = max(0, metrics["active_orders"] - 1)
                    return
            if stage["status"] == "In Kitchen":
                threading.Thread(target=lambda: requests.post(f"{KITCHEN_SERVICE}/prepare",
                    json={"order_id": oid, "platter_id": platter_id}, timeout=2), daemon=True).start()
            if stage["duration"] > 0:
                time.sleep(stage["duration"])
        if oid in orders:
            orders[oid]["completed_at"] = datetime.now().isoformat()
            metrics["completed"] += 1
            metrics["active_orders"] = max(0, metrics["active_orders"] - 1)
    except Exception as e:
        if oid in orders:
            orders[oid]["status"] = "Failed"
            orders[oid]["error"] = str(e)
        metrics["failures"] += 1
        metrics["active_orders"] = max(0, metrics["active_orders"] - 1)

@app.route("/order", methods=["POST", "OPTIONS"])
def create_order():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    start_time = time.time()
    metrics["total_requests"] += 1
    request_timestamps.append(time.time())
    data = request.json
    if not data:
        metrics["failures"] += 1
        return jsonify({"error": "Invalid JSON"}), 400
    platter_id = data.get("platter")
    student_id = data.get("student_id")
    idempotency_key = data.get("idempotency_key") or str(uuid.uuid4())
    if platter_id is None:
        metrics["failures"] += 1
        return jsonify({"error": "Missing platter"}), 400
    if not student_id:
        metrics["failures"] += 1
        return jsonify({"error": "Missing student_id"}), 400
    try:
        platter_id = int(platter_id)
    except (ValueError, TypeError):
        metrics["failures"] += 1
        return jsonify({"error": "Invalid platter ID"}), 400
    if idempotency_key in processed_order_ids:
        return jsonify({"error": "Duplicate order", "idempotent": True}), 409
    try:
        stock_check = requests.get(f"{STOCK_SERVICE}/platter/{platter_id}", timeout=1)
        if stock_check.status_code == 200:
            stock_data = stock_check.json()
            if stock_data.get("stock", 0) <= 0 and stock_data.get("cached"):
                return jsonify({"error": "Out of stock (cached)"}), 400
    except:
        pass
    oid = f"ORD-{int(time.time())}-{len(orders)+1}"
    processed_order_ids.add(idempotency_key)
    orders[oid] = {
        "id": oid, "platter_id": platter_id, "student_id": student_id,
        "status": "Pending", "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(), "idempotency_key": idempotency_key
    }
    metrics["active_orders"] += 1
    metrics["total_orders"] = len(orders)
    threading.Thread(target=process_order_async, args=(oid, platter_id, student_id), daemon=True).start()
    latency = (time.time() - start_time) * 1000
    metrics["latencies"].append(latency)
    return jsonify({"order_id": oid, "status": "Pending", "message": "Order created"})

@app.route("/status/<oid>", methods=["GET", "OPTIONS"])
def get_status(oid):
    if request.method == "OPTIONS":
        return jsonify({}), 200
    if oid not in orders:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(orders[oid])

@app.route("/metrics", methods=["GET"])
def get_metrics():
    now = time.time()
    recent = [ts for ts in request_timestamps if now - ts <= 60]
    rps = len(recent) / 60 if recent else 0
    avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"]) if metrics["latencies"] else 0
    return jsonify({
        "service": "order", "total_requests": metrics["total_requests"],
        "failures": metrics["failures"], "timeouts": metrics["timeouts"],
        "completed": metrics["completed"], "active_orders": metrics["active_orders"],
        "total_orders": metrics["total_orders"], "requests_per_second": round(rps, 2),
        "average_latency_ms": round(avg_latency, 2),
        "idempotent_orders": len(processed_order_ids)
    })

@app.route("/health", methods=["GET"])
def health():
    try:
        r = requests.get(f"{STOCK_SERVICE}/health", timeout=1)
        stock_status = "healthy" if r.status_code == 200 else "unhealthy"
    except:
        stock_status = "down"
    status_code = 200 if stock_status != "down" else 503
    return jsonify({
        "service": "order", "status": "online" if stock_status != "down" else "degraded",
        "dependencies": {"stock": stock_status}
    }), status_code

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 ORDER SERVICE RUNNING")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5002, debug=True, threaded=True)