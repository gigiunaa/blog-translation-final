from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import os
import traceback

app = Flask(__name__)

# =======================================
#  ROUTE 1: Extract <body> without styles
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

        # Save original (with styles)
        original_body = str(body)

        # 🧹 Remove inline styles, classes, IDs from all tags INCLUDING <body>
        for tag in body.find_all(True):
            tag.attrs = {}
        body.attrs = {}  # Also clean the <body> tag itself

        clean_body = str(body)

        return jsonify({
            "success": True,
            "clean_body": clean_body,     # send this to Make.com OpenAI module
            "original_body": original_body
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# =======================================
#  ROUTE 2: Rebuild translated HTML
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

        # Replace visible text only, keep styles
        original_tags = soup_original.find_all(["h1","h2","h3","h4","p","span","a","li","strong","em"])
        translated_tags = soup_translated.find_all(["h1","h2","h3","h4","p","span","a","li","strong","em"])

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
#  Health Check & Root
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
    print(f"🚀 Running unified HTML service on port {port}")
    app.run(host="0.0.0.0", port=port)
