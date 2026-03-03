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

def get_article_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers, timeout=5)
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
        'could', 'about', 'which', 'their', 'there', 'those', 'these', 'always'
    }
    good_words = [w for w in words if len(w) >= 7 and w not in common_words]
    # Lấy top 10 từ để đảm bảo không bị quá giới hạn thời gian chạy 10s của Vercel
    return Counter(good_words).most_common(10)

def find_example(word, sentences):
    for sentence in sentences:
        if re.search(r'\b' + re.escape(word) + r'\b', sentence.lower()):
            return sentence.replace('\n', ' ').strip()
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
            
            result_data.append({
                "word": word,
                "ipa": f"/{phonetic}/",
                "meaning": meaning,
                "frequency": freq,
                "example": example_sen
            })

        return jsonify({'vocab': result_data}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
