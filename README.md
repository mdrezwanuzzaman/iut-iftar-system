🍽️ IUT Iftar System
⚡ A Resilient Microservices-Based Smart Iftar Platform

Built for IUT Hackathon

🚀 Overview

IUT Iftar System is a production-inspired microservices web platform designed to manage Iftar meal ordering at IUT.

This is not just a CRUD app.
It demonstrates:

Distributed system design

JWT-based authentication

Service-to-service communication

Asynchronous processing

Caching strategies

Observability & metrics

Chaos engineering

🌙 The Problem

During Iftar time:

Long queues

Budget confusion

Manual tracking

No real-time status

Systems crash under load

We solved this using modern backend architecture principles.

🏗️ System Architecture

The system consists of 5 independent services.

                ┌─────────────────┐
                │   Gateway       │
                │    (5000)       │
                └────────┬────────┘
                         │
        ┌──────────┬──────────┬──────────┬──────────┐
        ▼          ▼          ▼          ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │Identity│  │ Order  │  │Kitchen │  │ Stock  │
   │ (5001) │  │ (5002) │  │ (5003) │  │ (5004) │
   └────────┘  └────────┘  └────────┘  └────────┘
🧠 Services
🌐 Gateway (Port 5000)

Single entry point

Routes all requests

Handles chaos toggling

Security enforcement

🔐 Identity Service (5001)

JWT authentication

Student budget management

Rate limiting (3 attempts/minute)

Student CRUD operations

🛒 Order Service (5002)

Order creation

Idempotency protection

Status lifecycle tracking

Metrics reporting

👨‍🍳 Kitchen Service (5003)

Asynchronous queue simulation

Delayed preparation

Status transitions

📦 Stock Service (5004)

Inventory management

TTL caching (5 seconds)

Quick rejection on zero stock

✨ Key Features
🔐 Security

JWT authentication

Protected routes

Budget validation

Rate limiting

⚡ Performance

In-memory stock caching

Optimized queries

Fast failure detection

🔄 Resilience

Asynchronous processing

Idempotent orders

Graceful degradation

Chaos engineering support

📊 Observability

Each service exposes:

/health

/metrics

Track:

Active orders

Total orders

Latency

Service uptime

👨‍🎓 Student Flow

Login securely

View live stock

Place order

Track real-time status

Order status flow:

Pending

Stock Verified

In Kitchen

Ready

Auto-refresh every 2 seconds.

👨‍💼 Admin Dashboard

Accessible at:

http://localhost:5000/admin

Features:

Live health grid

Order throughput

Latency monitoring

Remaining plates

Student management

Chaos toggles (Kill / Revive services)

🛠️ Tech Stack
Backend

Python 3.8+

Flask

SQLite

PyJWT

Requests

Cachetools

Flask-CORS

Frontend

HTML5

CSS3

Vanilla JavaScript

Jinja2

🧪 Testing

Run all tests:

python run_tests.py

Run with coverage:

coverage run -m unittest discover tests
coverage report -m

Includes:

38+ test cases

Edge case validation

Mocked dependencies

Error handling tests

⚙️ Installation

Clone the repository:

git clone https://github.com/your-username/iut-iftar-system.git
cd iut-iftar-system

Install dependencies:

pip install -r requirements.txt

Initialize database:

cd identity_service
python init_db.py
cd ..

Run services (5 terminals):

Terminal 1:

cd identity_service
python app.py

Terminal 2:

cd order_service
python app.py

Terminal 3:

cd kitchen_service
python app.py

Terminal 4:

cd stock_service
python app.py

Terminal 5:

cd gateway
python app.py

Access:

http://localhost:5000
🚀 Why This Stands Out

Real microservices architecture

Fault tolerance simulation

Observability built-in

Secure authentication

Performance optimization

Clean separation of concerns

This project demonstrates real distributed system thinking.

🌟 Future Improvements

Docker containerization

Kubernetes deployment

Redis caching

PostgreSQL migration

Load balancer

CI/CD pipeline

Cloud deployment

👥 Runtime Terror
Ayesha Chowdhury Aronti
Md Rezwan Uz Zaman
Takia Binte Enam
