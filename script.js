let currentVocabData = []; // Lưu trữ data để xuất CSV

// Xử lý Dark Mode
const themeToggle = document.getElementById('themeToggle');
const body = document.body;
if (localStorage.getItem('theme') === 'dark') {
    body.setAttribute('data-theme', 'dark');
    themeToggle.innerHTML = '<i class="fa-solid fa-sun"></i>';
}
themeToggle.addEventListener('click', () => {
    if (body.getAttribute('data-theme') === 'dark') {
        body.setAttribute('data-theme', 'light');
        themeToggle.innerHTML = '<i class="fa-solid fa-moon"></i>';
        localStorage.setItem('theme', 'light');
    } else {
        body.setAttribute('data-theme', 'dark');
        themeToggle.innerHTML = '<i class="fa-solid fa-sun"></i>';
        localStorage.setItem('theme', 'dark');
    }
});

// Chuyển Tab (URL vs Text)
let inputMode = 'url';
function switchTab(mode) {
    inputMode = mode;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));
    
    event.currentTarget.classList.add('active');
    document.getElementById(mode + 'Tab').classList.remove('hidden');
}

// Đọc phát âm Audio (Text to Speech)
function playAudio(word) {
    const utterance = new SpeechSynthesisUtterance(word);
    utterance.lang = 'en-US'; // Giọng Anh Mỹ
    utterance.rate = 0.9; // Đọc chậm lại 1 xíu cho dễ nghe
    window.speechSynthesis.speak(utterance);
}

// Hàm Highlight từ vựng trong câu ví dụ
function highlightWord(example, word) {
    if (!example) return "";
    // Dùng Regex tìm từ (không phân biệt hoa thường) và bọc thẻ <mark>
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    return example.replace(regex, `<mark>$&</mark>`);
}

// Xuất file CSV cho Anki
function downloadCSV() {
    if (currentVocabData.length === 0) return;
    
    let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // Thêm BOM để Excel đọc tiếng Việt không bị lỗi font
    csvContent += "Word,IPA,Meaning,Synonyms,Example\n"; // Header
    
    currentVocabData.forEach(item => {
        // Dọn dẹp dấu phẩy và ngoặc kép để không làm hỏng cấu trúc CSV
        let word = `"${item.word}"`;
        let ipa = `"${item.ipa}"`;
        let meaning = `"${item.meaning.replace(/"/g, '""')}"`;
        let syns = `"${item.synonyms}"`;
        let example = `"${item.example.replace(/"/g, '""')}"`;
        
        csvContent += `${word},${ipa},${meaning},${syns},${example}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "IELTS_Vocab_" + new Date().getTime() + ".csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Gọi API Phân tích
async function scrapeData() {
    const urlInput = document.getElementById('urlInput').value.trim();
    const textInput = document.getElementById('textInput').value.trim();
    const loading = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');
    const actionArea = document.getElementById('actionArea');

    let payload = {};
    if (inputMode === 'url') {
        if (!urlInput.startsWith('http')) {
            errorDiv.textContent = '❌ Vui lòng nhập link hợp lệ (bắt đầu bằng http hoặc https)!';
            errorDiv.classList.remove('hidden'); return;
        }
        payload = { url: urlInput };
    } else {
        if (textInput.length < 50) {
            errorDiv.textContent = '❌ Đoạn văn bản quá ngắn, vui lòng dán nhiều hơn!';
            errorDiv.classList.remove('hidden'); return;
        }
        payload = { text: textInput };
    }

    errorDiv.classList.add('hidden');
    actionArea.classList.add('hidden');
    resultDiv.innerHTML = '';
    loading.classList.remove('hidden');

    try {
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Lỗi hệ thống khi phân tích dữ liệu.');

        if (!data.vocab || data.vocab.length === 0) {
            errorDiv.textContent = 'Không tìm thấy từ vựng học thuật nào phù hợp.';
            errorDiv.classList.remove('hidden');
        } else {
            currentVocabData = data.vocab; // Lưu data để tải CSV
            actionArea.classList.remove('hidden'); // Hiện nút tải CSV

            data.vocab.forEach(item => {
                const card = document.createElement('div');
                card.className = 'card';
                const level = item.level || 'B1';
                const band = item.band || '5.0';
                
                // Highlight từ vựng trong ví dụ
                const highlightedEx = highlightWord(item.example, item.word);
                const synText = item.synonyms !== "N/A" ? `Đồng nghĩa: ${item.synonyms}` : '';

                card.innerHTML = `
                    <div class="card-header">
                        <div style="display:flex; align-items:center;">
                            <h3>${item.word}</h3>
                            <button class="play-audio" onclick="playAudio('${item.word}')" title="Nghe phát âm"><i class="fa-solid fa-volume-high"></i></button>
                        </div>
                        <span class="badge ${level.toLowerCase()}" title="IELTS ${band}">${level} | ${band}</span>
                    </div>
                    <div class="ipa">${item.ipa} <span>(lặp lại ${item.frequency} lần)</span></div>
                    <div class="meaning">${item.meaning}</div>
                    ${synText ? `<div class="synonyms"><i class="fa-solid fa-link"></i> ${synText}</div>` : ''}
                    <div class="example">
                        <strong>Ví dụ:</strong>
                        <div style="font-style: italic; margin-top:5px;">"${highlightedEx}"</div>
                    </div>
                `;
                resultDiv.appendChild(card);
            });
        }
    } catch (err) {
        errorDiv.textContent = '❌ ' + err.message;
        errorDiv.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}
