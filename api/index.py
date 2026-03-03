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
    """Đánh giá trình độ CEFR và IELTS Band"""
    length = len(word)
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
    sentences = []
    full_text_parts = []
    
    for p in paragraphs:
        # Lấy text, dọn dẹp các ký tự xuống dòng và khoảng trắng thừa
        text = p.get_text().replace('\n', ' ').replace('\r', '').strip()
        text = re.sub(r'\s+', ' ', text)
        if not text: continue
            
        full_text_parts.append(text)
        
        # THUẬT TOÁN TÁCH CÂU MỚI: Tách tại dấu . ! ? đi kèm khoảng trắng và chữ hoa
        # Giúp lấy được từng câu ngắn gọn, độc lập
        raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
        for s in raw_sentences:
            if len(s) > 15: # Chỉ lấy các câu có độ dài hợp lý, bỏ qua rác
                sentences.append(s.strip())

    full_text = ' '.join(full_text_parts)
    return full_text, sentences

def extract_words(text):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    common_words = {
        'because', 'through', 'between', 'another', 'without', 'however', 
        'against', 'during', 'before', 'number', 'people', 'should', 'would',
        'could', 'about', 'which', 'their', 'there', 'those', 'these', 'always', 'already'
    }
    good_words = [w for w in words if len(w) >= 7 and w not in common_words]
    return Counter(good_words).most_common(12)

def find_example(word, sentences):
    for sentence in sentences:
        # Tìm câu DUY NHẤT chứa từ vựng đó
        if re.search(r'\b' + re.escape(word) + r'\b', sentence.lower()):
            # Nếu câu vẫn hơi dài thì giới hạn lại khoảng 200 ký tự
            return sentence if len(sentence) <= 200 else sentence[:200] + "..."
    return "Không tìm thấy câu ví dụ phù hợp."

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"message": "API is running. Send POST to /api/scrape"}), 200

@app.route('/api/scrape', methods=['POST'])
def scrape_vocab():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url: return jsonify({'error': 'Vui lòng cung cấp URL'}), 400

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
