from flask import Flask, request, jsonify
from bs4 import BeautifulSoup, NavigableString

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)

# --- ფუნქცია 1: HTML-ის გასუფთავება ---
def sanitize_html(html_body):
    """
    აშორებს სტილის ატრიბუტებს (class, style), მაგრამ ინარჩუნებს
    სტრუქტურას და მნიშვნელოვან ატრიბუტებს (href, src).
    """
    if not html_body:
        return ""
        
    soup = BeautifulSoup(html_body, 'html.parser')
    attributes_to_keep = ['href', 'src', 'alt', 'id']
    
    for tag in soup.find_all(True):
        kept_attrs = {}
        if tag.attrs:
            for attr, value in tag.attrs.items():
                if attr in attributes_to_keep:
                    kept_attrs[attr] = value
            tag.attrs = kept_attrs
            
    return str(soup)

# --- ფუნქცია 2: სტილების აღდგენა ---
def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
    """
    იღებს საწყის სტილიან და ნათარგმნ სუფთა HTML-ს.
    ნათარგმნი ტექსტი გადააქვს საწყის სტრუქტურაში სტილების აღსადგენად.
    """
    if not original_styled_html or not translated_clean_html:
        return original_styled_html

    original_soup = BeautifulSoup(original_styled_html, 'html.parser')
    translated_soup = BeautifulSoup(translated_clean_html, 'html.parser')

    def sync_text_nodes(original_element, translated_element):
        original_children = list(original_element.children)
        translated_children = list(translated_element.children)

        for i in range(min(len(original_children), len(translated_children))):
            orig_child, trans_child = original_children[i], translated_children[i]

            if orig_child.name is not None and trans_child.name is not None and orig_child.name == trans_child.name:
                sync_text_nodes(orig_child, trans_child)
            elif isinstance(orig_child, NavigableString) and isinstance(trans_child, NavigableString):
                if orig_child.string and orig_child.string.strip():
                    orig_child.string.replace_with(trans_child.string)

    sync_text_nodes(original_soup, translated_soup)
    return str(original_soup)

# --- API მისამართები (Endpoints) ---

@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    """
    API მისამართი HTML-ის გასასუფთავებლად.
    მოელის JSON-ს: {"html": "<body>..."}
    აბრუნებს JSON-ს: {"clean_html": "<p>..."}
    """
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "მოთხოვნაში აკლია 'html' ველი"}), 400
    
    html_input = data['html']
    clean_html = sanitize_html(html_input)
    
    return jsonify({"clean_html": clean_html})

@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    """
    API მისამართი სტილების აღსადგენად.
    მოელის JSON-ს: {"original_html": "...", "translated_html": "..."}
    აბრუნებს JSON-ს: {"final_html": "..."}
    """
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return jsonify({"error": "მოთხოვნაში აკლია 'original_html' ან 'translated_html' ველი"}), 400
    
    original_html = data['original_html']
    translated_html = data['translated_html']
    
    final_html = restore_styles_to_translated_html(original_html, translated_html)
    
    return jsonify({"final_html": final_html})

# აპლიკაციის გაშვება (Render.com ამას არ იყენებს, ის Gunicorn-ს იყენებს)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
