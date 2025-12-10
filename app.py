# <<<< ცვლილება 1: "from flask" ხაზის განახლება >>>>
from flask import Flask, request, jsonify, Response 
from bs4 import BeautifulSoup, NavigableString

# >>> NEW IMPORTS FOR LINK CLEANING <<<
from urllib.parse import urlparse, parse_qs, urlunparse
import re

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)


# -----------------------------------------------
# >>> NEW HELPER FUNCTIONS FOR LINK PROCESSING <<<
# -----------------------------------------------

SUPPORTED_LANGS = {"en", "ka", "es", "de", "pt", "ru"}

def extract_real_url_from_google(url):
    """
    Google redirect: ამოიღებს q= რეალურ URL-ს.
    """
    normalized = url.replace("&amp;", "&")
    parsed = urlparse(normalized)

    if "google.com" not in parsed.netloc or not parsed.path.startswith("/url"):
        return url

    qs = parse_qs(parsed.query)
    return qs.get("q", [url])[0]


def rewrite_gegidze_language(url, lang):
    """
    gegidze.com URL-ზე ენის პრეფიქსის ჩასმა.
    """
    parsed = urlparse(url)

    if "gegidze.com" not in parsed.netloc:
        return url

    if lang not in SUPPORTED_LANGS:
        lang = "en"

    segments = [s for s in parsed.path.split("/") if s]

    # remove existing language prefix
    if segments and segments[0] in SUPPORTED_LANGS:
        segments = segments[1:]

    # add new prefix
    if lang == "en":
        new_path = "/" + "/".join(segments)
    else:
        new_path = f"/{lang}/" + "/".join(segments)

    return urlunparse(parsed._replace(path=new_path))


# ------------------------
# სრულად **არსებული კოდი**
# ------------------------

# --- ფუნქცია 1: HTML-ის გასუფთავება (უცვლელია) ---
def sanitize_html(html_body):
    """
    აშორებს სტილის ატრიბუტებს (class, style), მაგრამ ინარჩუნებს
    სტრუქტურას და მნიშვნელოვან ატრიბუტებს (href, src).
    """
    if not html_body:
        return ""
        
    soup = BeautifulSoup(html_body, 'html.parser')
    # დავამატე 'title', რადგან ის შეიძლება მნიშვნელოვანი იყოს
    attributes_to_keep = ['href', 'src', 'alt', 'id', 'title']
    
    for tag in soup.find_all(True):
        kept_attrs = {}
        if tag.attrs:
            for attr, value in tag.attrs.items():
                if attr in attributes_to_keep:
                    kept_attrs[attr] = value
            tag.attrs = kept_attrs
            
    return str(soup)

# --- სტილების აღდგენა (არსებული) ---
def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
    """
    იღებს საწყის სტილიან და ნათარგმნ სუფთა HTML-ს.
    ნათარგმნი ტექსტი გადააქვს საწყის სტრუქტურაში სტილების აღსადგენად.
    """
    if not original_styled_html or not translated_clean_html:
        return original_styled_html

    original_soup = BeautifulSoup(original_styled_html, 'html.parser')
    translated_soup = BeautifulSoup(translated_clean_html, 'html.parser')

    original_text_nodes = [node for node in original_soup.find_all(string=True) if node.strip()]
    translated_text_nodes = [node for node in translated_soup.find_all(string=True) if node.strip()]

    for i in range(min(len(original_text_nodes), len(translated_text_nodes))):
        if original_text_nodes[i] and translated_text_nodes[i]:
            original_text_nodes[i].replace_with(str(translated_text_nodes[i]))
        
    return str(original_soup)

# --- sanitize endpoint ---
@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "მოთხოვნაში აკლია 'html' ველი"}), 400
    
    html_input = data['html']

    soup = BeautifulSoup(html_input, 'html.parser')
    body_content = soup.find('body')
    if not body_content:
        body_content = soup
    
    clean_html = sanitize_html(str(body_content))
    
    return jsonify({"clean_html": clean_html})

# --- restore-styles endpoint ---
@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return Response("{\"error\": \"მოთხოვნაში აკლია 'original_html' ან 'translated_html' ველი\"}",
                        status=400, mimetype='application/json')
    
    original_html = data['original_html']
    translated_html = data['translated_html']
    
    original_soup = BeautifulSoup(original_html, 'html.parser')
    original_body = original_soup.find('body') or original_soup
        
    translated_soup = BeautifulSoup(translated_html, 'html.parser')
    translated_body = translated_soup.find('body') or translated_soup
    
    final_html_string = restore_styles_to_translated_html(str(original_body), str(translated_body))
    
    return Response(final_html_string, mimetype='text/html; charset=utf-8')


# ---------------------------------------------------
# >>> ახალი /clean-links endpoint (მხოლოდ `<a href>`)
# ---------------------------------------------------
@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    """
    იღებს მთელ HTML-ს.
    მხოლოდ <a href=""> ლინკებს ასუფთავებს:
      ✔ ამოითვლის Google redirect-ს
      ✔ თუ gegidze.com → ჩაანაცვლებს ენის პრეფიქსს
    აბრუნებს HTML-ს ხელუხლებლად (გარდა href).
    """

    data = request.get_json()
    if not data or "html" not in data:
        return jsonify({"error": "Missing 'html' field"}), 400

    html = data["html"]
    lang = data.get("lang", "en")

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        new_url = href

        if "google.com/url" in href:
            new_url = extract_real_url_from_google(href)

        if "gegidze.com" in new_url:
            new_url = rewrite_gegidze_language(new_url, lang)

        tag["href"] = new_url

    return jsonify({"clean_html": str(soup)})


# --- app run ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
