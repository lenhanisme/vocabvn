async function scrapeData() {
    const urlInput = document.getElementById('urlInput').value.trim();
    const loading = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const errorDiv = document.getElementById('error');

    if (!urlInput.startsWith('http')) {
        errorDiv.textContent = '❌ Vui lòng nhập link hợp lệ (bắt đầu bằng http)!';
        errorDiv.classList.remove('hidden');
        return;
    }

    // Reset giao diện
    errorDiv.classList.add('hidden');
    resultDiv.innerHTML = '';
    loading.classList.remove('hidden');

    try {
        // Gọi API backend của chính trang web
        const response = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi hệ thống khi cào dữ liệu.');
        }

        if (data.vocab.length === 0) {
            errorDiv.textContent = 'Không tìm thấy từ vựng nào phù hợp.';
            errorDiv.classList.remove('hidden');
        } else {
            // Render từng từ vựng ra giao diện
            data.vocab.forEach(item => {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <h3>${item.word}</h3>
                    <div class="ipa">${item.ipa} <span>(lặp lại ${item.frequency} lần)</span></div>
                    <div class="meaning">${item.meaning}</div>
                    <div class="example"><strong>Ví dụ:</strong> <i>"${item.example}"</i></div>
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
