import os
import requests
from flask import Flask, jsonify
from google.auth.transport.requests import Request
from google.oauth2 import id_token


app = Flask(__name__)

INTERNAL_SERVICE_URL = os.environ.get("INTERNAL_SERVICE_URL")
GCP_PROJECT = os.environ.get("GCP_PROJECT", "local")
AUTH_MODE = os.environ.get("AUTH_MODE", "gcp")


def fetch_identity_token(audience):
    auth_request = Request()
    return id_token.fetch_id_token(auth_request, audience)

@app.get("/health")
def health():
    return "ok", 200

@app.get("/api/orders")
def get_orders():
    if not INTERNAL_SERVICE_URL:
        return jsonify({"error": "INTERNAL_SERVICE_URL is not set"}), 500

    try:
        if AUTH_MODE == "gcp":
            token = fetch_identity_token(INTERNAL_SERVICE_URL)
            headers = {"Authorization": f"Bearer {token}"}
        elif AUTH_MODE == "local":
            headers = {}
        else:
            return jsonify({"error": "Invalid AUTH_MODE"}), 500

        resp = requests.get(
            f"{INTERNAL_SERVICE_URL}/internal/orders",
            headers=headers,
            timeout=10,
        )
    except Exception as exc:
        return jsonify(
            {
                "error": "failed to call internal service",
                "detail": str(exc),
                "hint": "Check AUTH_MODE and INTERNAL_SERVICE_URL",
            }
        ), 502

    if resp.status_code == 403:
        return jsonify(
            {
                "error": "internal service returned 403",
                "hint": "Check internal service authorization",
                "body": resp.text,
            }
        ), 403

    if not resp.ok:
        return jsonify(
            {
                "error": "internal service error",
                "status": resp.status_code,
                "body": resp.text,
            }
        ), 502

    data = resp.json()
    return jsonify(
        {
            "source": "public-api",
            "project": GCP_PROJECT,
            "internal": data,
        }
    )