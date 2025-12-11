from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urlparse, parse_qs, urlunparse

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)

# --- ფუნქცია 1: HTML-ის გასუფთავება (უცვლელია) ---
def sanitize_html(html_body):
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

# --- ფუნქცია 2: სტილების აღდგენა (უცვლელია) ---
def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
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

# --- ფუნქცია 3: ლინკების დამუშავება (შესწორებულია - არ ცვლის სტრუქტურას) ---
def clean_and_localize_links(html_content, lang):
    """
    1. ასუფთავებს Google Redirect-ებს.
    2. ამატებს ენის პრეფიქსს (მაგ: /de/) შიდა ლინკებზე.
    3. გარე ლინკებს უკეთებს target="_blank"-ს.
    ABSOLUTELY NO STRUCTURAL CHANGES. Returns full HTML including head/styles.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    my_domain = 'gegidze.com'  # შენი დომენი

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']

        # 1. Google Redirect-ის მოცილება
        if 'google.com/url' in href and 'q=' in href:
            try:
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                clean_url = query_params.get('q', [None])[0]
                if clean_url:
                    href = clean_url
            except Exception as e:
                print(f"Error parsing URL: {e}")

        # 2. ენის პრეფიქსის დამატება (Localization)
        if lang and lang != 'en':
            is_internal = my_domain in href or href.startswith('/')
            has_prefix = href.startswith(f'/{lang}/') or (f'{my_domain}/{lang}/' in href)

            if is_internal and not has_prefix:
                try:
                    parsed = urlparse(href)
                    # თუ ლინკი იწყება /-ით ან შეიცავს დომენს
                    path = parsed.path
                    if not path.startswith(f'/{lang}'):
                         # ახალი path-ის აწყობა
                        new_path = f'/{lang}{path}' if path.startswith('/') else f'/{lang}/{path}'
                        # URL-ის თავიდან აწყობა (scheme, netloc, path, params, query, fragment)
                        href = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))
                except Exception as e:
                    print(f"Localization error: {e}")

        # 3. SEO: External Links (target="_blank")
        if my_domain not in href and not href.startswith('/') and not href.startswith('#'):
            a_tag['target'] = '_blank'
            a_tag['rel'] = 'noopener noreferrer'

        # ვანახლებთ href ატრიბუტს
        a_tag['href'] = href

    # <<<< ცვლილება: ვაბრუნებთ მთლიან soup-ს და არა body-ს >>>>
    return str(soup)


# --- API მისამართები (Endpoints) ---

@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "No 'html' field"}), 400
    
    html_input = data['html']
    soup = BeautifulSoup(html_input, 'html.parser')
    body_content = soup.find('body') or soup
    
    clean_html = sanitize_html(str(body_content))
    return jsonify({"clean_html": clean_html})

@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return Response("{\"error\": \"Missing fields\"}", status=400, mimetype='application/json')
    
    original_body = BeautifulSoup(data['original_html'], 'html.parser').find('body') or BeautifulSoup(data['original_html'], 'html.parser')
    translated_body = BeautifulSoup(data['translated_html'], 'html.parser').find('body') or BeautifulSoup(data['translated_html'], 'html.parser')
    
    final_html_string = restore_styles_to_translated_html(str(original_body), str(translated_body))
    return Response(final_html_string, mimetype='text/html; charset=utf-8')

# --- <<<< ახალი ენდპოინტი ლინკებისთვის >>>> ---
@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    """
    API ლინკების გასასუფთავებლად და ლოკალიზაციისთვის.
    Input JSON: { "html": "...", "lang": "de" }
    Output JSON: { "cleaned_html": "..." }
    """
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "მოთხოვნაში აკლია 'html' ველი"}), 400
    
    html_input = data['html']
    lang = data.get('lang', 'en') # დიფოლტად 'en'
    
    cleaned_html = clean_and_localize_links(html_input, lang)
    
    return jsonify({"cleaned_html": cleaned_html})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
