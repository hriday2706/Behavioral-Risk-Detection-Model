"""
SentinelFlow Application Entry Point.
Provides REST API endpoints for session tracking, feature extraction,
risk inference, and policy-enforced banking actions.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import config

def create_app(test_config=None) -> Flask:
    app = Flask(__name__)
    CORS(app)

    if test_config:
        app.config.update(test_config)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "SentinelFlow Risk Engine",
            "version": "1.0.0-hackathon-poc",
            "policy_version": "demo-policy-v1"
        }), 200

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
