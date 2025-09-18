from flask import Flask, jsonify, request
app = Flask(__name__)

@app.get("/")
def health():
    return jsonify(ok=True, runtime="python3.11")

@app.post("/summarize")
def summarize():
    data = request.get_json(silent=True) or {}
    return jsonify(success=True, echo=data)

if __name__ == "__main__":
    app.run(debug=True, port=5001)