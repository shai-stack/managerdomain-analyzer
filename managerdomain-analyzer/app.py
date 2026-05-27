import asyncio
import re
from flask import Flask, request, jsonify, render_template_string
from analyzer import analyze_domains

app = Flask(__name__)


def clean_domain(d: str) -> str:
    d = d.strip()
    d = re.sub(r'^https?://', '', d)
    d = d.rstrip('/')
    return d


@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json() or {}
    raw = data.get('domains', [])
    domains = list(dict.fromkeys(clean_domain(d) for d in raw if d.strip()))[:250]
    domains = [d for d in domains if d]
    results = asyncio.run(analyze_domains(domains))
    return jsonify(results)


HTML = "<html><body><h1>MANAGERDOMAIN Analyzer</h1></body></html>"


if __name__ == '__main__':
    print("\n  MANAGERDOMAIN Analyzer")
    print("  Open in your browser: http://localhost:5050\n")
    app.run(host='127.0.0.1', port=5050, debug=False)
