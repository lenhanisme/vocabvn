from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import eng_to_ipa as ipa
from deep_translator import GoogleTranslator

app = Flask(__name__)
CORS(app)

def estimate_level(word):
    """Đánh giá trình độ CEFR và IELTS Band dựa trên cấu trúc từ"""
    length = len(word)
    # Các đuôi từ thường gặp ở trình độ cao
    c1_c2_suffixes = ('tion', 'ment', 'ence', 'ance', 'ility', 'ology', 'esque', 'cious')
    
    if length >= 10 or word.endswith(c1_c2_suffixes):
        return {"level": "C1", "band": "7.0+"}
    elif length >= 8:
        return {"level": "B2", "band": "6.0-6.5"}
    else:
        return {"level": "B1", "band": "5.0-5.5"}

def get_article_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status() 
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    full_text = ' '.join([p.get_text() for p in paragraphs])
    sentences = re.split(r'(?<=[.!?]) +', full_text)
    return full_text, sentences

def extract_words(text):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    common_words = {
        'because', 'through', 'between', 'another', 'without', 'however', 
        'against', 'during', 'before', 'number', 'people', 'should', 'would',
        'could', 'about', 'which', 'their', 'there', 'those', 'these', 'always', 'already'
    }
    good_words = [w for w in words if len(w) >= 7 and w not in common_words]
    return Counter(good_words).most_common(12) # Lấy 12 từ cho đẹp UI (chia hết cho 1, 2, 3 cột)

def find_example(word, sentences):
    for sentence in sentences:
        if re.search(r'\b' + re.escape(word) + r'\b', sentence.lower()):
            # Loại bỏ khoảng trắng thừa
            clean_sentence = sentence.replace('\n', ' ').strip()
            # Nếu câu quá dài thì ngắt bớt ở Backend luôn cho nhẹ dữ liệu
            return clean_sentence if len(clean_sentence) <= 250 else clean_sentence[:250] + "..."
    return ""

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"message": "API is running. Send POST to /api/scrape"}), 200

@app.route('/api/scrape', methods=['POST'])
def scrape_vocab():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'error': 'Vui lòng cung cấp URL'}), 400

        full_text, sentences = get_article_data(url)
        top_vocab = extract_words(full_text)
        
        translator = GoogleTranslator(source='en', target='vi')
        result_data = []

        for word, freq in top_vocab:
            phonetic = ipa.convert(word)
            if '*' in phonetic: phonetic = "N/A"
            
            try:
                meaning = translator.translate(word)
            except:
                meaning = "Lỗi dịch thuật"
                
            example_sen = find_example(word, sentences)
            word_stats = estimate_level(word)
            
            result_data.append({
                "word": word,
                "ipa": f"/{phonetic}/",
                "meaning": meaning,
                "frequency": freq,
                "example": example_sen,
                "level": word_stats["level"],
                "band": word_stats["band"]
            })

        return jsonify({'vocab': result_data}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
