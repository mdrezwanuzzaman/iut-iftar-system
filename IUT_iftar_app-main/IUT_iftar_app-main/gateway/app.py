from flask import Flask, request, jsonify, render_template
import requests
import time
import jwt
from functools import wraps
from cachetools import TTLCache

app = Flask(__name__)
SECRET = "iftar-secret-key"

# Service URLs
IDENTITY = "http://127.0.0.1:5001"
ORDER = "http://127.0.0.1:5002"
STOCK = "http://127.0.0.1:5004"
KITCHEN = "http://127.0.0.1:5003"

# Cache for stock (TTL: 5 seconds)
stock_cache = TTLCache(maxsize=100, ttl=5)

# Chaos mode tracking
chaos_state = {}
latency_history = []


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            data = jwt.decode(token, SECRET, algorithms=["HS256"])
            current_user = data['student_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


def check_service_available(service):
    return not chaos_state.get(service, False)


@app.after_request
def after_request(response):
    if request.path.startswith('/api/'):
        latency = response.headers.get('X-Process-Time')
        if latency:
            latency_history.append({
                'time': time.time(),
                'latency': float(latency)
            })
            latency_history[:] = [l for l in latency_history if time.time() - l['time'] <= 30]

    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# -----------------------
# PAGE ROUTES
# -----------------------

@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/menu")
def menu_page():
    return render_template("menu.html")


@app.route("/status/<oid>")
def status_page(oid):
    return render_template("status.html", order_id=oid)


@app.route("/ready/<oid>")
def ready_page(oid):
    return render_template("ready.html", oid=oid)


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


# -----------------------
# API ROUTES
# -----------------------

@app.route("/api/login", methods=["POST", "OPTIONS"])
def api_login():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    start_time = time.time()

    if not check_service_available("identity"):
        return jsonify({"error": "Identity Service Down (Chaos Mode)"}), 503

    try:
        r = requests.post(f"{IDENTITY}/login", json=request.json, timeout=5)
        response = jsonify(r.json()), r.status_code
    except requests.exceptions.ConnectionError:
        response = jsonify({"error": "Identity Service Unavailable"}), 503
    except Exception as e:
        response = jsonify({"error": str(e)}), 500

    if isinstance(response, tuple) and len(response) == 2:
        response[0].headers['X-Process-Time'] = str((time.time() - start_time) * 1000)

    return response


@app.route("/api/budget/<student_id>")
@token_required
def api_budget(current_user, student_id):
    if current_user != student_id:
        return jsonify({"error": "Unauthorized"}), 403

    if not check_service_available("identity"):
        return jsonify({"budget": 0})

    try:
        r = requests.get(f"{IDENTITY}/budget/{student_id}", timeout=3)
        return jsonify(r.json())
    except:
        return jsonify({"budget": 0})


@app.route("/api/stock/<int:platter>")
def api_stock(platter):
    cache_key = f"platter_{platter}"
    if cache_key in stock_cache:
        return jsonify({**stock_cache[cache_key], "cached": True})

    if not check_service_available("stock"):
        mock_stock = {
            1: {"stock": 45, "max_stock": 120, "prep_time": 5, "popular": False},
            2: {"stock": 30, "max_stock": 80, "prep_time": 8, "popular": False},
            3: {"stock": 15, "max_stock": 50, "prep_time": 10, "popular": False}
        }
        return jsonify(mock_stock.get(platter, {"stock": 0}))

    try:
        r = requests.get(f"{STOCK}/platter/{platter}", timeout=2)
        if r.status_code == 200:
            data = r.json()
            stock_cache[cache_key] = data
            return jsonify(data)
    except:
        pass

    return jsonify({"stock": 0})


@app.route("/api/order", methods=["POST"])
@token_required
def api_order(current_user):
    start_time = time.time()
    data = request.json
    platter = data.get("platter")
    student_id = data.get("student_id")

    if current_user != student_id:
        return jsonify({"error": "Unauthorized"}), 403

    prices = {1: 120, 2: 180, 3: 250}
    amount = prices.get(platter, 0)

    cache_key = f"platter_{platter}"
    if cache_key in stock_cache and stock_cache[cache_key].get("stock", 0) <= 0:
        return jsonify({"error": "Out of stock (cached)"}), 400

    try:
        if check_service_available("stock"):
            stock_response = requests.get(f"{STOCK}/platter/{platter}", timeout=2)
            if stock_response.status_code == 200:
                stock_data = stock_response.json()
                if stock_data.get("stock", 0) <= 0:
                    return jsonify({"error": "Item out of stock"}), 400

        if check_service_available("identity"):
            deduct_response = requests.post(
                f"{IDENTITY}/deduct",
                json={"student_id": student_id, "amount": amount},
                timeout=3
            )
            if deduct_response.status_code != 200:
                return jsonify({"error": "Failed to deduct budget"}), 400

        order_response = requests.post(
            f"{ORDER}/order",
            json={
                "platter": platter,
                "student_id": student_id,
                "idempotency_key": f"{student_id}_{int(time.time())}"
            },
            timeout=5
        )

        if order_response.status_code != 200:
            return jsonify({"error": "Failed to create order"}), 500

        response = jsonify(order_response.json()), 200

    except requests.exceptions.ConnectionError:
        response = jsonify({"error": "Service unavailable"}), 503
    except Exception as e:
        response = jsonify({"error": str(e)}), 500

    if isinstance(response, tuple) and len(response) == 2:
        response[0].headers['X-Process-Time'] = str((time.time() - start_time) * 1000)

    return response


@app.route("/api/status/<oid>")
def api_status(oid):
    if not check_service_available("order"):
        return jsonify({"status": "Unknown", "chaos": True}), 503

    try:
        r = requests.get(f"{ORDER}/status/{oid}", timeout=3)
        return jsonify(r.json())
    except:
        return jsonify({"status": "Unknown"}), 503


@app.route("/api/plates")
def api_plates():
    if not check_service_available("stock"):
        return jsonify({"plates": 0})

    try:
        r = requests.get(f"{STOCK}/plates", timeout=2)
        return jsonify(r.json())
    except:
        return jsonify({"plates": 0})


# -----------------------
# CHAOS ENGINE
# -----------------------

@app.route("/api/chaos/kill/<service>", methods=["POST"])
def kill_service(service):
    if service in ["identity", "order", "stock", "kitchen"]:
        chaos_state[service] = True
        return jsonify({"status": "chaos_mode", "service": service})
    return jsonify({"error": "Service not found"}), 404


@app.route("/api/chaos/revive/<service>", methods=["POST"])
def revive_service(service):
    if service in chaos_state:
        del chaos_state[service]
        return jsonify({"status": "revived", "service": service})
    return jsonify({"error": "Service not found"}), 404


@app.route("/api/chaos/status")
def chaos_status():
    return jsonify({"chaos_state": chaos_state})


def check_latency_alert():
    now = time.time()
    recent = [l for l in latency_history if now - l['time'] <= 30]
    if recent:
        avg = sum(l['latency'] for l in recent) / len(recent)
        return avg > 1000
    return False


# -----------------------
# HEALTH & METRICS
# -----------------------

@app.route("/api/health")
def health():
    services = {
        "identity": f"{IDENTITY}/health",
        "order": f"{ORDER}/health",
        "stock": f"{STOCK}/health",
        "kitchen": f"{KITCHEN}/health"
    }

    result = {}
    all_healthy = True

    for name, url in services.items():
        if chaos_state.get(name):
            result[name] = {"service": name, "status": "down", "chaos": True}
            all_healthy = False
            continue

        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                data = r.json()
                data["status"] = "online"
                result[name] = data
            else:
                result[name] = {"service": name, "status": "error"}
                all_healthy = False
        except:
            result[name] = {"service": name, "status": "down"}
            all_healthy = False

    result["gateway"] = {
        "service": "gateway",
        "status": "online",
        "cache_size": len(stock_cache),
        "latency_alert": check_latency_alert()
    }

    result["overall"] = "healthy" if all_healthy else "degraded"
    return jsonify(result)


@app.route("/api/metrics")
def gateway_metrics():
    return jsonify({
        "service": "gateway",
        "cache_hits": len(stock_cache),
        "chaos_active": len(chaos_state) > 0,
        "latency_alert": check_latency_alert()
    })


if __name__ == "__main__":
    print("=" * 60)
    print("🔥 IFTAR GATEWAY - HACKATHON EDITION")
    print("=" * 60)
    print("📍 Token Validation: Enabled")
    print("📍 Cache: Enabled (TTL: 5s)")
    print("📍 Chaos Engine: Ready")
    print("\n📍 Services:")
    print(f"   Identity: {IDENTITY}")
    print(f"   Order: {ORDER}")
    print(f"   Stock: {STOCK}")
    print(f"   Kitchen: {KITCHEN}")
    print("\n📍 URLs:")
    print("   Main App:  http://localhost:5000")
    print("   Admin:     http://localhost:5000/admin")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)