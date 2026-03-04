# 🍽️ IUT Iftar System

A microservices-based Iftar ordering system for IUT Hackathon.

## ✨ Features

- ✅ JWT Authentication with Rate Limiting (3 attempts/min)
- ✅ Real-time Order Tracking (Pending → Stock → Kitchen → Ready)
- ✅ Live Stock Updates with Caching
- ✅ Admin Dashboard with Service Health Monitoring
- ✅ Chaos Engineering (Kill/Revive services)
- ✅ Idempotency (No duplicate orders)
- ✅ Async Kitchen Processing
- ✅ Visual Alerts for High Latency
- ✅ Student Management (Add/Remove/Add Money)

## 🏗️ Architecture

- **Gateway** (Port 5000) - Main entry point
- **Identity** (Port 5001) - Auth & budget
- **Order** (Port 5002) - Order processing
- **Kitchen** (Port 5003) - Meal prep
- **Stock** (Port 5004) - Inventory

## 🚀 Quick Start

### Windows
```bash
double-click start_all.bat