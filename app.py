from flask import Flask, request, jsonify, Response # <<<< 1. დავამატეთ Response იმპორტი

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
    attributes_to_keep = ['href', 'src', 'alt', 'id', 'title'] # დავამატე title, ყოველი შემთხვევისთვის
    
    for tag in soup.find_all(True):
        kept_attrs = {}
        if tag.attrs:
            for attr, value in tag.attrs.items():
                if attr in attributes_to_keep:
                    kept_attrs[attr] = value
            tag.attrs = kept_attrs
            
    return str(soup)

# --- ფუნქცია 2: სტილების აღდგენა (განახლებული ლოგიკა უკეთესი სიზუსტისთვის) ---
def restore_styles_to_translated_html(original_styled_html, translated_clean_html):
    """
    იღებს საწყის სტილიან და ნათარგმნ სუფთა HTML-ს.
    ნათარგმნი ტექსტი გადააქვს საწყის სტრუქტურაში სტილების აღსადგენად.
    """
    if not original_styled_html or not translated_clean_html:
        return original_styled_html

    original_soup = BeautifulSoup(original_styled_html, 'html.parser')
    translated_soup = BeautifulSoup(translated_clean_html, 'html.parser')

    # ვიპოვოთ ყველა ტექსტური ფრაგმენტი ორივე დოკუმენტში
    original_text_nodes = [node for node in original_soup.find_all(string=True) if node.strip()]
    translated_text_nodes = [node for node in translated_soup.find_all(string=True) if node.strip()]

    # შევცვალოთ ტექსტები თანმიმდევრობით
    for i in range(min(len(original_text_nodes), len(translated_text_nodes))):
        # ვცვლით მხოლოდ იმ შემთხვევაში, თუ ტექსტი ნამდვილად არსებობს
        if original_text_nodes[i] and translated_text_nodes[i]:
            original_text_nodes[i].replace_with(str(translated_text_nodes[i]))
        
    return str(original_soup)

# --- API მისამართები (Endpoints) ---

# --- /sanitize მისამართი (მცირე შესწორებით, რომ მხოლოდ body-სთან იმუშაოს) ---
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
    
    # დავრწმუნდეთ, რომ მხოლოდ body-ს შიგთავსს ვამუშავებთ
    soup = BeautifulSoup(html_input, 'html.parser')
    body_content = soup.find('body')
    if not body_content:
        body_content = soup # თუ body თეგი არ არის, ვიღებთ მთლიან დოკუმენტს
        
    clean_html = sanitize_html(str(body_content))
    
    return jsonify({"clean_html": clean_html})

# --- <<<< 2. მთავარი ცვლილება აქ არის >>>> ---
@app.route('/restore-styles', methods=['POST'])
def handle_restore_styles():
    """
    API მისამართი სტილების აღსადგენად.
    მოელის JSON-ს: {"original_html": "...", "translated_html": "..."}
    აბრუნებს სუფთა HTML-ს (text/html) და არა JSON-ს.
    """
    data = request.get_json()
    if not data or 'original_html' not in data or 'translated_html' not in data:
        # შეცდომის დაბრუნებაც Response ობიექტით
        return Response("{\"error\": \"მოთხოვნაში აკლია 'original_html' ან 'translated_html' ველი\"}", status=400, mimetype='application/json')
    
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
    
    final_html_string = restore_styles_to_translated_html(str(original_body), str(translated_body))
    
    # შედეგს ვაბრუნებთ როგორც სუფთა HTML ტექსტს
    return Response(final_html_string, mimetype='text/html; charset=utf-8')

# --- <<<< ცვლილება აქ მთავრდება >>>> ---

# აპლიკაციის გაშვება (Render.com ამას არ იყენებს, ის Gunicorn-ს იყენებს)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
