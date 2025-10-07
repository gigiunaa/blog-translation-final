from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import os
import traceback

app = Flask(__name__)

# =======================================
# ROUTE 1: Extract <body> — fully cleaned
# =======================================
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

        original_body = str(body)

        # Remove all attributes recursively (style, class, id, data-*, etc.)
        for tag in body.find_all(True):
            for attr in list(tag.attrs.keys()):
                del tag[attr]

        clean_body = str(body)

        return jsonify({
            "success": True,
            "clean_body": clean_body,
            "original_body": original_body
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# =======================================
# ROUTE 2: Rebuild translated HTML
# =======================================
@app.route("/rebuild-styles", methods=["POST"])
def rebuild_styles():
    try:
        data = request.get_json()
        original_body = data.get("original_body")
        translated_text = data.get("translated_text")

        if not original_body or not translated_text:
            return jsonify({"success": False, "error": "Missing fields"}), 400

        soup_original = BeautifulSoup(original_body, "html.parser")
        soup_translated = BeautifulSoup(translated_text, "html.parser")

        # Replace text nodes while preserving structure and styles
        original_tags = soup_original.find_all(["h1", "h2", "h3", "h4", "p", "span", "a", "li", "strong", "em"])
        translated_tags = soup_translated.find_all(["h1", "h2", "h3", "h4", "p", "span", "a", "li", "strong", "em"])

        for o_tag, t_tag in zip(original_tags, translated_tags):
            if t_tag and t_tag.get_text(strip=True):
                o_tag.string = t_tag.get_text(strip=True)

        return jsonify({
            "success": True,
            "translated_html": str(soup_original)
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# =======================================
# Root (Health check)
# =======================================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "HTML Extractor & Styler",
        "endpoints": ["/extract-body", "/rebuild-styles"],
        "status": "running"
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"🚀 Running HTML translator microservice on port {port}")
    app.run(host="0.0.0.0", port=port)
