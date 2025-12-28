from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urlparse, urlunparse, unquote
import re
import json

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)

# ========================================================
# 1. Sanitize (უცვლელი)
# ========================================================
def sanitize_html(html_body):
    if not html_body:
        return ""
        
    soup = BeautifulSoup(html_body, 'html.parser')
    attributes_to_keep = ['href', 'src', 'alt', 'id', 'title', 'target']
    
    for tag in soup.find_all(True):
        kept_attrs = {}
        if tag.attrs:
            for attr, value in tag.attrs.items():
                if attr in attributes_to_keep:
                    kept_attrs[attr] = value
            tag.attrs = kept_attrs
            
    return str(soup)

# ========================================================
# 2. Restore Styles (შეცვლილი — REPLACE, არა MERGE)
# ========================================================
def restore_styles_to_translated_html(original_html, translated_html):
    """
    NEW LOGIC:
    - No text merging
    - No node index mapping
    - Translated HTML fully replaces text content
    - Prevents duplicated text (EN+DE)
    """

    if not translated_html:
        return original_html

    translated_soup = BeautifulSoup(translated_html, 'html.parser')
    translated_body = translated_soup.find('body')

    # თუ GPT აბრუნებს body-ს — პირდაპირ ვაბრუნებთ
    if translated_body:
        return str(translated_body)

    # თუ body საერთოდ არ აქვს (edge case)
    return str(translated_soup)

# ========================================================
# 3. Restore Styles V2 (დარჩა, მაგრამ აღარ გამოიყენება)
# ========================================================
def restore_styles_v2(original_html, translated_html):
    if not original_html or not translated_html:
        return original_html

    original_soup = BeautifulSoup(original_html, 'html.parser')
    translated_soup = BeautifulSoup(translated_html, 'html.parser')

    TEXT_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'a']

    def extract_text_elements(soup):
        elements = []
        for tag in soup.find_all(TEXT_TAGS):
            if tag.find('img'):
                continue
            if tag.get_text(strip=True):
                elements.append(tag)
        return elements

    original_elements = extract_text_elements(original_soup)
    translated_elements = extract_text_elements(translated_soup)

    limit = min(len(original_elements), len(translated_elements))

    for i in range(limit):
        original_el = original_elements[i]
        translated_el = translated_elements[i]

        for child in list(original_el.children):
            if isinstance(child, NavigableString):
                child.extract()

        original_el.append(translated_el.get_text())

    return str(original_soup)

# ========================================================
# 4. Clean Links — Gegidze (უცვლელი)
# ========================================================
def process_url(href, lang, my_domain="gegidze.com"):
    google_pattern = r'[?&]q=([^&]+)'
    if "google.com/url" in href:
        match = re.search(google_pattern, href)
        if match:
            href = unquote(match.group(1))

    if lang and lang != 'en':
        try:
            parsed = urlparse(href)
            is_internal = my_domain in parsed.netloc or (not parsed.netloc and parsed.path)
            
            if is_internal and not parsed.path.startswith(f'/{lang}/'):
                new_path = f'/{lang}{parsed.path}' if parsed.path.startswith('/') else f'/{lang}/{parsed.path}'
                href = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
        except Exception as e:
            print(f"Localization error: {e}")

    return href

def clean_and_localize_links(html_content, lang):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        new_href = process_url(a['href'], lang)
        a['href'] = new_href
        
        if (
            "gegidze.com" not in new_href
            and not new_href.startswith('/')
            and not new_href.startswith('#')
        ):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

    return str(soup)

# ========================================================
# 5. Clean Links — Team Up (უცვლელი)
# ========================================================
def process_url_teamup(href, lang, my_domain="helloteamup.com"):
    google_pattern = r'[?&]q=([^&]+)'
    if "google.com/url" in href:
        match = re.search(google_pattern, href)
        if match:
            href = unquote(match.group(1))

    if lang and lang != 'en':
        try:
            parsed = urlparse(href)
            is_internal = my_domain in parsed.netloc or (not parsed.netloc and parsed.path)
            
            if is_internal and not parsed.path.startswith(f'/{lang}/'):
                new_path = f'/{lang}{parsed.path}' if parsed.path.startswith('/') else f'/{lang}/{parsed.path}'
                href = urlunparse((
                    parsed.scheme,
                    parsed.netloc,
                    new_path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
        except Exception as e:
            print(f"Localization error: {e}")

    return href

def clean_and_localize_links_teamup(html_content, lang):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        new_href = process_url_teamup(a['href'], lang)
        a['href'] = new_href
        
        if (
            "helloteamup.com" not in new_href
            and not new_href.startswith('/')
            and not new_href.startswith('#')
        ):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

    return str(soup)

# ========================================================
# API Endpoints
# ========================================================

@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "No 'html' field"}), 400
    
    soup = BeautifulSoup(data['html'], 'html.parser')
    body = soup.find('body') or soup
    return jsonify({"clean_html": sanitize_html(str(body))})

@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return Response(
            '{"error":"Missing fields"}',
            status=400,
            mimetype='application/json'
        )

    return Response(
        restore_styles_to_translated_html(
            data['original_html'],
            data['translated_html']
        ),
        mimetype='text/html; charset=utf-8'
    )

@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    data = request.get_json()
    if not data or 'html' not in data:
        return Response('"error":"Missing html"', status=400, mimetype='text/plain')

    result_html = clean_and_localize_links(data['html'], data.get('lang', 'en'))
    return Response(f'"html":{json.dumps(result_html)}', mimetype='text/plain')

@app.route('/clean-links-teamup', methods=['POST'])
def handle_clean_links_teamup():
    data = request.get_json()
    if not data or 'html' not in data:
        return Response('"error":"Missing html"', status=400, mimetype='text/plain')

    result_html = clean_and_localize_links_teamup(data['html'], data.get('lang', 'en'))
    return Response(f'"html":{json.dumps(result_html)}', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
