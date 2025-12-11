from flask import Flask, request, Response
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlunparse, unquote
import re
import json

app = Flask(__name__)

# --- დამხმარე ფუნქცია: URL-ის დამუშავება ---
def process_url(href, lang, my_domain="gegidze.com"):
    # Google Redirect (Regex-ით)
    google_pattern = r'[?&]q=([^&]+)'
    if "google.com/url" in href:
        match = re.search(google_pattern, href)
        if match:
            href = unquote(match.group(1))

    # Localization
    if lang and lang != 'en':
        try:
            parsed = urlparse(href)
            is_internal = my_domain in parsed.netloc or (not parsed.netloc and parsed.path)
            
            if is_internal:
                if not parsed.path.startswith(f'/{lang}/'):
                    new_path = f'/{lang}{parsed.path}' if parsed.path.startswith('/') else f'/{lang}/{parsed.path}'
                    href = urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))
        except Exception as e:
            print(f"Link error: {e}")

    return href

# --- მთავარი ფუნქცია ---
def clean_and_localize_links(html_content, lang):
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, 'html.parser')
    
    for a in soup.find_all('a', href=True):
        original_href = a['href']
        new_href = process_url(original_href, lang)
        a['href'] = new_href
        
        if "gegidze.com" not in new_href and not new_href.startswith('/') and not new_href.startswith('#'):
            a['target'] = '_blank'
            a['rel'] = 'noopener noreferrer'

    # აქ მნიშვნელოვანია: str(soup) აბრუნებს სუფთა HTML-ს, მაგრამ JSON-ისთვის escape სჭირდება
    return str(soup)

# --- Endpoints ---

@app.route('/clean-links', methods=['POST'])
def handle_clean_links():
    data = request.get_json()
    if not data or 'html' not in data:
        return Response('"error":"Missing html"', status=400, mimetype='text/plain')
    
    html_input = data['html']
    lang = data.get('lang', 'en')
    
    # ვიღებთ დამუშავებულ HTML-ს
    result_html = clean_and_localize_links(html_input, lang)
    
    # JSON-ის "Escape" რომ გაუკეთოს (ბრჭყალებს \ დაუმატოს), ვიყენებთ json.dumps-ს
    escaped_html = json.dumps(result_html) 
    
    # ვაწყობთ ზუსტად იმ სტრინგს, რაც გინდა: "html":"<html>..."
    # json.dumps-ს მოაქვს ბრჭყალები თავში და ბოლოში, ამიტომ პირდაპირ ვიყენებთ
    final_response_string = f'"html":{escaped_html}'
    
    # ვაბრუნებთ როგორც უბრალო ტექსტს (text/plain)
    return Response(final_response_string, mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
