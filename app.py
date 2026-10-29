"""
SentinelFlow Application Entry Point.
Serves both the REST API and the banking demo frontend.
"""

from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from backend.database import init_db
from backend.routes import api_bp
import config

def create_app(test_config=None) -> Flask:
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    app = Flask(__name__, static_folder=str(frontend_dir), static_url_path="/static")
    CORS(app)

    if test_config:
        app.config.update(test_config)

    # Initialize SQLite database
    init_db()

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "SentinelFlow Risk Engine",
            "version": "1.0.0-hackathon-poc",
            "policy_version": "demo-policy-v1"
        }), 200

    @app.route("/", methods=["GET"])
    def serve_index():
        return send_from_directory(str(frontend_dir), "index.html")

    @app.route("/<path:path>", methods=["GET"])
    def serve_frontend_assets(path):
        return send_from_directory(str(frontend_dir), path)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
