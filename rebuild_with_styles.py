# =========================
# FILE: rebuild_with_styles.py
# PURPOSE: Merges translated text back into original HTML with styles
# =========================

from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import os

app = Flask(__name__)

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

        # Replace only visible text nodes in matching tags
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
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    print(f"🚀 rebuild_with_styles running on port {port}")
    app.run(host="0.0.0.0", port=port)
