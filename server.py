from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import bot_logic
import logging
import sys
import os

app = Flask(__name__, 
            static_folder='../frontend',
            template_folder='../frontend')
CORS(app)

@app.route('/')
def serve_frontend():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"""
        <html>
            <body>
                <h1>Instagram Bot</h1>
                <p>Frontend tidak ditemukan. Pastikan file index.html ada di folder frontend.</p>
                <p>Error: {str(e)}</p>
                <p>Current directory: {os.getcwd()}</p>
            </body>
        </html>
        """

@app.route('/api/run-bot', methods=['POST'])
def run_bot():
    try:
        # Log untuk debugging
        print("✅ API /api/run-bot dipanggil")
        print(f"✅ Data received: {request.json}")
        
        data = request.json
        
        # Validasi data yang diperlukan
        required_fields = ['accounts_input', 'target_post', 'comments_input']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Field {field} harus diisi'
                }), 400
        
        config = {
            'accounts_input': data['accounts_input'],
            'target_post': data['target_post'],
            'comments_input': data['comments_input'],
            'max_comments': data.get('max_comments', 1),
            'iterations': data.get('iterations', 1),
            'delay_after_like': data.get('delay_after_like', 5),
            'delay_after_comment': data.get('delay_after_comment', 5),
            'delay_between_accounts': data.get('delay_between_accounts', 5),
            'delay_between_rounds': data.get('delay_between_rounds', 10),
            'proxy': data.get('proxy', '')
        }
        
        result = bot_logic.run_bot(config)
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error in /api/run-bot: {e}")
        return jsonify({
            'success': False,
            'message': f'Terjadi kesalahan server: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'Server is running',
        'endpoints': {
            'home': '/',
            'run_bot': '/api/run-bot',
            'health': '/api/health'
        }
    })

@app.route('/<path:path>')
def serve_static_files(path):
    try:
        return app.send_static_file(path)
    except:
        return "File tidak ditemukan", 404

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Instagram Bot Server Starting...")
    print("📁 Current directory:", os.getcwd())
    print("🌐 Server will run at: http://localhost:5000")
    print("✅ Endpoints available:")
    print("   - http://localhost:5000/ (Frontend)")
    print("   - http://localhost:5000/api/health (Health Check)")
    print("   - http://localhost:5000/api/run-bot (Run Bot)")
    print("=" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Tips: Port 5000 mungkin sudah digunakan. Coba ganti port.")