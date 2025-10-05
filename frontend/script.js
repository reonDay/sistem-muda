let isRunning = false;
const BACKEND_URL = 'http://localhost:5000'; // Pastikan URL ini sesuai

// Fungsi untuk test koneksi ke server
async function testConnection() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            addLog(`✅ Terhubung ke server: ${data.message}`);
            return true;
        } else {
            addLog('❌ Server tidak merespons dengan baik');
            return false;
        }
    } catch (error) {
        addLog('❌ Tidak dapat terhubung ke server');
        addLog('💡 Pastikan server backend sudah berjalan:');
        addLog('   - Buka Command Prompt/Terminal');
        addLog('   - Masuk ke folder backend');
        addLog('   - Jalankan: python server.py');
        return false;
    }
}

// Tambah log
function addLog(message) {
    const logDisplay = document.getElementById('logDisplay');
    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    
    const now = new Date();
    const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    logItem.textContent = `[${timeString}] ${message}`;
    logDisplay.appendChild(logItem);
    
    logDisplay.scrollTop = logDisplay.scrollHeight;
}

// Update progress
function updateProgress(percent, status) {
    document.getElementById('progressFill').style.width = percent + '%';
    document.getElementById('statusText').textContent = status;
}

// Tampilkan hasil
function showResults(stats) {
    const resultsSection = document.getElementById('results');
    const resultsContent = document.getElementById('resultsContent');
    
    let html = `
        <p><strong>Total komentar dikirim:</strong> ${stats.total_comments}</p>
        <p><strong>Akun yang berhasil:</strong> ${stats.active_accounts} dari ${stats.total_accounts}</p>
        <p><strong>Rincian per akun:</strong></p>
        <ul style="margin-left: 20px;">
    `;
    
    for (const [username, count] of Object.entries(stats.account_details)) {
        html += `<li>${username}: ${count} komentar</li>`;
    }
    
    html += `</ul>`;
    resultsContent.innerHTML = html;
    resultsSection.style.display = 'block';
}

// Jalankan bot
async function runBot() {
    if (isRunning) return;
    
    // Test koneksi dulu
    addLog('🔍 Mengecek koneksi ke server...');
    const connected = await testConnection();
    
    if (!connected) {
        updateProgress(0, 'Gagal terhubung ke server');
        return;
    }

    // Ambil data dari form
    const config = {
        accounts_input: document.getElementById('accounts').value,
        target_post: document.getElementById('target').value,
        comments_input: document.getElementById('comments').value,
        max_comments: parseInt(document.getElementById('maxComments').value),
        iterations: parseInt(document.getElementById('iterations').value),
        delay_after_like: 5,
        delay_after_comment: 5,
        delay_between_accounts: 5,
        delay_between_rounds: 10,
        proxy: ''
    };

    // Validasi sederhana
    if (!config.accounts_input.trim()) {
        alert('Harap isi data akun Instagram');
        return;
    }
    if (!config.target_post.trim()) {
        alert('Harap isi URL postingan target');
        return;
    }
    if (!config.comments_input.trim()) {
        alert('Harap isi daftar komentar');
        return;
    }

    // Set status menjalankan
    isRunning = true;
    document.getElementById('runBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    
    // Reset log dan progress
    document.getElementById('logDisplay').innerHTML = '';
    document.getElementById('results').style.display = 'none';
    
    addLog('🚀 Memulai bot...');
    updateProgress(20, 'Memproses data...');

    try {
        addLog('📡 Mengirim data ke server...');
        
        const response = await fetch(`${BACKEND_URL}/api/run-bot`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });

        addLog('✅ Data terkirim, menunggu respons...');

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            addLog('✅ ' + result.message);
            updateProgress(100, 'Selesai!');
            
            if (result.stats) {
                showResults(result.stats);
            }
        } else {
            addLog('❌ ' + result.message);
            updateProgress(0, 'Proses gagal');
        }
        
    } catch (error) {
        addLog('❌ ERROR: ' + error.message);
        addLog('💡 Pastikan:');
        addLog('   1. Server backend berjalan');
        addLog('   2. Tidak ada firewall yang memblokir');
        addLog('   3. Port 5000 tersedia');
        updateProgress(0, 'Gagal terhubung');
    } finally {
        isRunning = false;
        document.getElementById('runBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
    }
}

// Hentikan bot
function stopBot() {
    if (isRunning) {
        isRunning = false;
        document.getElementById('runBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        addLog('⏹️ Bot dihentikan');
        updateProgress(0, 'Dihentikan');
    }
}

// Inisialisasi
document.addEventListener('DOMContentLoaded', function() {
    addLog('Sistem siap. Isi formulir di atas dan klik JALANKAN BOT.');
    
    // Auto test connection setelah 2 detik
    setTimeout(() => {
        addLog('🔍 Auto-test koneksi server...');
        testConnection();
    }, 2000);
});