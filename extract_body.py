# =========================
# FILE: extract_body.py
# PURPOSE: Extracts clean <body> (text-only, no styles)
# =========================

from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

@app.route("/extract-body", methods=["POST"])
def extract_body():
    try:
        data = request.get_json()
        html = data.get("html")
        if not html:
            return jsonify({"success": False, "error": "Missing HTML"}), 400

        soup = BeautifulSoup(html, "html.parser")
        body = soup.find("body")
        if not body:
            return jsonify({"success": False, "error": "No <body> found"}), 400

        # Save the original version (with styles)
        original_body = str(body)

        # Remove all inline styles, classes, and attributes
        for tag in body.find_all(True):
            tag.attrs = {}

        clean_body = str(body)

        return jsonify({
            "success": True,
            "clean_body": clean_body,     # send to Make.com OpenAI module
            "original_body": original_body
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 extract_body running on port {port}")
    app.run(host="0.0.0.0", port=port)
