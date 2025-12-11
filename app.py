from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse

app = Flask(__name__)

# --- დამხმარე ფუნქცია: URL-ის დამუშავება ---
def process_url(href, lang, my_domain="gegidze.com"):
    # 1. Google Redirect-ის მოცილება
    if "google.com/url" in href and "q=" in href:
        try:
            parsed = urlparse(href)
            query = parse_qs(parsed.query)
            if 'q' in query:
                href = query['q'][0]
        except Exception as e:
            print(f"URL parsing error: {e}")

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

# --- მთავარი ფუნქცია: მხოლოდ ლინკების შეცვლა ---
def clean_and_localize_links(html_content, lang):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # ვეძებთ და ვცვლით მხოლოდ ლინკებს
    for a in soup.find_all('a', href=True):
        original_href = a['href']
        new_href = process_url(original_href, lang)
        a['href'] = new_href
        
        # SEO: External Links
        if "gegidze.com" not in new_href and not new_href.startswith('/') and not new_href.startswith('#'):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

    # ვაბრუნებთ მთლიან სტრუქტურას (<html>...</html>)
    return str(soup)

# --- Endpoints ---

@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    """
    Input JSON: { "html": "...", "lang": "de" }
    Output JSON: { "html": "..." }  <-- აქ შევცვალე გასაღები
    """
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "Missing 'html' field"}), 400
    
    html_input = data['html']
    lang = data.get('lang', 'en')
    
    # ამუშავებს მხოლოდ ლინკებს, სტრუქტურა რჩება ხელშეუხებელი
    result_html = clean_and_localize_links(html_input, lang)
    
    # ვაბრუნებთ ისევ "html" გასაღებით, რომ Make-ში მარტივი იყოს
    return jsonify({"html": result_html})

# (ძველი ენდპოინტები სურვილისამებრ)
@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    data = request.get_json()
    return jsonify({"clean_html": data.get('html', '')}) 

@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    data = request.get_json()
    return Response(data.get('original_html', ''), mimetype='text/html; charset=utf-8')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
