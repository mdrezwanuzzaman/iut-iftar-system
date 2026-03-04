#!/usr/bin/env python3
"""
Iftar System - One Click Launcher
"""

import os
import sys
import subprocess
import time
import webbrowser
import platform
import signal


def print_color(text, color):
    colors = {'green': '\033[92m', 'red': '\033[91m', 'blue': '\033[94m', 'reset': '\033[0m'}
    if platform.system() == 'Windows':
        print(text)
    else:
        print(f"{colors.get(color, '')}{text}{colors['reset']}")


def kill_process_on_port(port):
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(f'netstat -ano | findstr :{port}', shell=True, capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        else:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, capture_output=True)
    except:
        pass


def main():
    print("=" * 60)
    print_color("   IFTAR SYSTEM - ONE CLICK LAUNCHER", 'green')
    print("=" * 60)
    print()

    print_color("[1/6] Cleaning up ports...", 'blue')
    for port in [5000, 5001, 5002, 5003, 5004]:
        kill_process_on_port(port)
    print_color("   ✅ Ports cleaned", 'green')

    print_color("[2/6] Initializing database...", 'blue')
    if platform.system() == 'Windows':
        subprocess.run('cd identity_service && python init_db.py', shell=True)
    else:
        subprocess.run('cd identity_service && python3 init_db.py', shell=True)
    print_color("   ✅ Database ready", 'green')

    print_color("[3/6] Starting services...", 'blue')

    services = [
        ("Identity", "5001", "identity_service", "app.py"),
        ("Order", "5002", "order_service", "app.py"),
        ("Kitchen", "5003", "kitchen_service", "app.py"),
        ("Stock", "5004", "stock_service", "app.py"),
        ("Gateway", "5000", "gateway", "app.py")
    ]

    for name, port, folder, script in services:
        print(f"   Starting {name} Service...")
        if platform.system() == 'Windows':
            cmd = f'start "{name} Service" cmd /k "cd {folder} && python {script}"'
            subprocess.Popen(cmd, shell=True)
        else:
            cmd = f'cd {folder} && python3 {script}'
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    print_color("   ✅ All services started", 'green')

    print_color("[4/6] Waiting for services...", 'blue')
    time.sleep(5)
    print_color("   ✅ Services ready", 'green')

    print()
    print_color("=" * 60, 'green')
    print_color("   ✅ SYSTEM IS RUNNING!", 'green')
    print_color("=" * 60, 'green')
    print()
    print("   📍 Access URLs:")
    print("      🏠 Main App:  http://localhost:5000")
    print("      📊 Admin:     http://localhost:5000/admin")
    print()

    print_color("[5/6] Opening browser...", 'blue')
    webbrowser.open('http://localhost:5000')
    print_color("   ✅ Browser opened", 'green')

    print()
    print_color("   Press Ctrl+C to stop all services", 'yellow')
    print_color("[6/6] System ready! Enjoy! 🎉", 'green')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        print_color("\n🛑 Stopping services...", 'blue')
        for port in [5000, 5001, 5002, 5003, 5004]:
            kill_process_on_port(port)
        print_color("   ✅ Services stopped", 'green')
        print_color("\n👋 Goodbye!", 'green')


if __name__ == "__main__":
    main()