from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urlparse, parse_qs, urlunparse, unquote
import re

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)

# ==========================================
# 1. ძველი ფუნქციები (უცვლელი)
# ==========================================

def sanitize_html(html_body):
    """
    აშორებს სტილის ატრიბუტებს, მაგრამ ინარჩუნებს სტრუქტურას.
    """
    if not html_body:
        return ""
        
    soup = BeautifulSoup(html_body, 'html.parser')
    attributes_to_keep = ['href', 'src', 'alt', 'id', 'title']
    
    for tag in soup.find_all(True):
        kept_attrs = {}
        if tag.attrs:
            for attr, value in tag.attrs.items():
                if attr in attributes_to_keep:
                    kept_attrs[attr] = value
            tag.attrs = kept_attrs
            
    return str(soup)

def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
    """
    აღადგენს სტილებს ნათარგმნ ტექსტზე.
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

# ==========================================
# 2. ახალი ფუნქცია (ლინკების გასწორება)
# ==========================================

def process_url(href, lang, my_domain="gegidze.com"):
    # 1. Google Redirect-ის მოცილება (Regex-ით, ყველაზე საიმედო)
    google_pattern = r'[?&]q=([^&]+)'
    if "google.com/url" in href:
        match = re.search(google_pattern, href)
        if match:
            href = unquote(match.group(1))

    # 2. ენის პრეფიქსის დამატება (Localization)
    if lang and lang != 'en':
        try:
            parsed = urlparse(href)
            # ვამოწმებთ არის თუ არა შიდა ლინკი
            is_internal = my_domain in parsed.netloc or (not parsed.netloc and parsed.path)
            
            if is_internal:
                if not parsed.path.startswith(f'/{lang}/'):
                    new_path = f'/{lang}{parsed.path}' if parsed.path.startswith('/') else f'/{lang}/{parsed.path}'
                    href = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))
        except Exception as e:
            print(f"Localization error: {e}")

    return href

def clean_and_localize_links(html_content, lang):
    """
    ცვლის მხოლოდ ლინკებს. არ ეხება HTML-ის სტრუქტურას.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        original_href = a['href']
        new_href = process_url(original_href, lang)
        a['href'] = new_href
        
        # SEO: External Links
        if "gegidze.com" not in new_href and not new_href.startswith('/') and not new_href.startswith('#'):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

    # აბრუნებს სრულ HTML-ს (head, body, styles - ყველაფერს)
    return str(soup)

# ==========================================
# 3. API Endpoints
# ==========================================

@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "No 'html' field"}), 400
    
    html_input = data['html']
    soup = BeautifulSoup(html_input, 'html.parser')
    body_content = soup.find('body')
    if not body_content:
        body_content = soup
    
    clean_html = sanitize_html(str(body_content))
    return jsonify({"clean_html": clean_html})

@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return Response('{"error": "Missing fields"}', status=400, mimetype='application/json')
    
    original_body = BeautifulSoup(data['original_html'], 'html.parser').find('body') or BeautifulSoup(data['original_html'], 'html.parser')
    translated_body = BeautifulSoup(data['translated_html'], 'html.parser').find('body') or BeautifulSoup(data['translated_html'], 'html.parser')
    
    final_html_string = restore_styles_to_translated_html(str(original_body), str(translated_body))
    return Response(final_html_string, mimetype='text/html; charset=utf-8')

@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "Missing 'html' field"}), 400
    
    html_input = data['html']
    lang = data.get('lang', 'en')
    
    # აქ ვიძახებთ ახალ ფუნქციას, რომელიც სტრუქტურას ინარჩუნებს
    result_html = clean_and_localize_links(html_input, lang)
    
    return jsonify({"html": result_html})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
