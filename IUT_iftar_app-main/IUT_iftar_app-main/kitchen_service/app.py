from flask import Flask, jsonify, request
import threading
import time
import queue
from datetime import datetime

app = Flask(__name__)

kitchen_queue = queue.Queue()
active_jobs = {}
completed_jobs = set()
metrics = {"total_jobs": 0, "completed": 0, "failed": 0}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

def worker():
    while True:
        try:
            job = kitchen_queue.get(timeout=1)
            active_jobs[job["order_id"]] = {"status": "preparing", "started_at": datetime.now().isoformat()}
            time.sleep(job.get("prep_time", 5))
            active_jobs[job["order_id"]]["status"] = "completed"
            completed_jobs.add(job["order_id"])
            metrics["completed"] += 1
        except queue.Empty:
            time.sleep(0.1)
        except:
            metrics["failed"] += 1

threading.Thread(target=worker, daemon=True).start()

@app.route("/prepare", methods=["POST", "OPTIONS"])
def prepare():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.json
    kitchen_queue.put({
        "order_id": data.get("order_id"), "platter_id": data.get("platter_id"),
        "prep_time": data.get("prep_time", 5), "received_at": datetime.now().isoformat()
    })
    metrics["total_jobs"] += 1
    return jsonify({"status": "accepted", "order_id": data.get("order_id")}), 202

@app.route("/metrics", methods=["GET"])
def get_metrics():
    return jsonify({
        "service": "kitchen", "total_jobs": metrics["total_jobs"],
        "completed": metrics["completed"], "failed": metrics["failed"],
        "queue_size": kitchen_queue.qsize()
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"service": "kitchen", "status": "online", "time": time.time()})

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 KITCHEN SERVICE RUNNING")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5003, debug=True, threaded=True)