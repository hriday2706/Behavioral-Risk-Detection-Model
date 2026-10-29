"""
SentinelFlow Main Entry Point.
Run this file to launch the SentinelFlow demo server.
"""

from app import app

if __name__ == "__main__":
    print("=" * 60)
    print("SentinelFlow: Behavior-Based Risk Level Prediction System")
    print("Banking Demo Server running at: http://127.0.0.1:5000")
    print("API Documentation & Health at: http://127.0.0.1:5000/api/health")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False)
