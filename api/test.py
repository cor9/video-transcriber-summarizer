from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'working',
        'message': 'VidScribe2AI is running',
        'assemblyai_key': bool(os.getenv("ASSEMBLYAI_API_KEY")),
        'anthropic_key': bool(os.getenv("ANTHROPIC_API_KEY"))
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True)
