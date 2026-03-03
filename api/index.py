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
    length = len(word)
    c1_c2_suffixes = ('tion', 'ment', 'ence', 'ance', 'ility', 'ology', 'esque', 'cious')
    if length >= 10 or word.endswith(c1_c2_suffixes): return {"level": "C1", "band": "7.0+"}
    elif length >= 8: return {"level": "B2", "band": "6.0-6.5"}
    else: return {"level": "B1", "band": "5.0-5.5"}

# Tính năng mới: Lấy từ đồng nghĩa qua API miễn phí Datamuse
def get_synonyms(word):
    try:
        res = requests.get(f"https://api.datamuse.com/words?rel_syn={word}&max=3", timeout=2)
        if res.status_code == 200:
            data = res.json()
            if data:
                return ", ".join([w['word'] for w in data])
        return "N/A"
    except:
        return "N/A"

def extract_text_and_sentences(raw_text):
    text = raw_text.replace('\n', ' ').replace('\r', '').strip()
    text = re.sub(r'\s+', ' ', text)
    sentences = []
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
    for s in raw_sentences:
        if len(s) > 15: sentences.append(s.strip())
    return text, sentences

def get_article_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers, timeout=8)
    response.raise_for_status() 
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    
    full_text_parts = []
    sentences = []
    for p in paragraphs:
        text, sents = extract_text_and_sentences(p.get_text())
        if text: full_text_parts.append(text)
        sentences.extend(sents)

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
        if re.search(r'\b' + re.escape(word) + r'\b', sentence.lower()):
            return sentence if len(sentence) <= 200 else sentence[:200] + "..."
    return "Không có ví dụ."

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return jsonify({"message": "API is running."}), 200

@app.route('/api/scrape', methods=['POST'])
def scrape_vocab():
    try:
        data = request.get_json()
        
        # Xử lý 2 trường hợp: Nhập URL hoặc Dán Text
        if 'url' in data and data['url']:
            full_text, sentences = get_article_data(data['url'])
        elif 'text' in data and data['text']:
            full_text, sentences = extract_text_and_sentences(data['text'])
        else:
            return jsonify({'error': 'Vui lòng cung cấp URL hoặc Text'}), 400

        top_vocab = extract_words(full_text)
        translator = GoogleTranslator(source='en', target='vi')
        result_data = []

        for word, freq in top_vocab:
            phonetic = ipa.convert(word)
            if '*' in phonetic: phonetic = "N/A"
            try: meaning = translator.translate(word)
            except: meaning = "Lỗi dịch thuật"
                
            example_sen = find_example(word, sentences)
            word_stats = estimate_level(word)
            synonyms = get_synonyms(word) # Gọi hàm lấy từ đồng nghĩa
            
            result_data.append({
                "word": word,
                "ipa": f"/{phonetic}/",
                "meaning": meaning,
                "synonyms": synonyms,
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
