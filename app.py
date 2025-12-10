# <<<< ცვლილება 1: "from flask" ხაზის განახლება >>>>
from flask import Flask, request, jsonify, Response
from bs4 import BeautifulSoup, NavigableString

# Flask აპლიკაციის ინიციალიზაცია
app = Flask(__name__)

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

# --- <<<< ცვლილება 2: სტილების აღდგენის ფუნქციის ლოგიკის გაუმჯობესება >>>> ---
def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
    """
    იღებს საწყის სტილიან და ნათარგმნ სუფთა HTML-ს.
    ნათარგმნი ტექსტი გადააქვს საწყის სტრუქტურაში სტილების აღსადგენად.
    """
    if not original_styled_html or not translated_clean_html:
        return original_styled_html

    original_soup = BeautifulSoup(original_styled_html, 'html.parser')
    translated_soup = BeautifulSoup(translated_clean_html, 'html.parser')

    # ეს მეთოდი უფრო საიმედოა - პირდაპირ ცვლის ტექსტურ ფრაგმენტებს
    original_text_nodes = [node for node in original_soup.find_all(string=True) if node.strip()]
    translated_text_nodes = [node for node in translated_soup.find_all(string=True) if node.strip()]

    for i in range(min(len(original_text_nodes), len(translated_text_nodes))):
        if original_text_nodes[i] and translated_text_nodes[i]:
            original_text_nodes[i].replace_with(str(translated_text_nodes[i]))
        
    return str(original_soup)

# --- API მისამართები (Endpoints) ---
@app.route('/sanitize', methods=['POST'])
def handle_sanitize():
    """
    API მისამართი HTML-ის გასასუფთავებლად.
    მოელის JSON-ს: {"html": "..."}
    აბრუნებს JSON-ს: {"clean_html": "..."}
    """
    data = request.get_json()
    if not data or 'html' not in data:
        return jsonify({"error": "მოთხოვნაში აკლია 'html' ველი"}), 400
    
    html_input = data['html']

    # დავრწმუნდეთ, რომ მხოლოდ body-სთან ვმუშაობთ
    soup = BeautifulSoup(html_input, 'html.parser')
    body_content = soup.find('body')
    if not body_content:
        body_content = soup
    
    clean_html = sanitize_html(str(body_content))
    
    return jsonify({"clean_html": clean_html})

# --- <<<< ცვლილება 3: /restore-styles ენდპოინტის სრული ჩანაცვლება >>>> ---
@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    """
    API მისამართი სტილების აღსადგენად.
    მოელის JSON-ს: {"original_html": "...", "translated_html": "..."}
    აბრუნებს სუფთა HTML-ს (text/html) და არა JSON-ს.
    """
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        return Response(
            "{\"error\": \"მოთხოვნაში აკლია 'original_html' ან 'translated_html' ველი\"}",
            status=400,
            mimetype='application/json'
        )
    
    original_html = data['original_html']
    translated_html = data['translated_html']
    
    # დავრწმუნდეთ, რომ ორივე შემთხვევაში მხოლოდ body-სთან ვმუშაობთ
    original_soup = BeautifulSoup(original_html, 'html.parser')
    original_body = original_soup.find('body')
    if not original_body:
        original_body = original_soup
        
    translated_soup = BeautifulSoup(translated_html, 'html.parser')
    translated_body = translated_soup.find('body')
    if not translated_body:
        translated_body = translated_soup
    
    final_html_string = restore_styles_to_translated_html(
        str(original_body), 
        str(translated_body)
    )
    
    # შედეგს ვაბრუნებთ როგორც სუფთა HTML ტექსტს, UTF-8 კოდირებით
    return Response(final_html_string, mimetype='text/html; charset=utf-8')

# აპლიკაციის გაშვება (Render.com ამას არ იყენებს, ის Gunicorn-ს იყენებს)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
