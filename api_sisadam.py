import os
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# O Render define a porta automaticamente através de uma variável de ambiente
PORT = int(os.environ.get("PORT", 5000))

@app.route('/salvar-token', methods=['POST'])
def salvar_token():
    dados = request.json
    # AQUI: O seu computador da portaria vai buscar esses dados periodicamente
    # Por enquanto, apenas confirmamos o recebimento
    print(f"Token recebido: {dados.get('apartamento')}")
    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)