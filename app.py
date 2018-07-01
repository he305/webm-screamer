from flask import Flask, request
from detector import get_data
import json
from flask import jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

@app.route("/api/", methods=['GET', 'POST'])
def hello():
    jobs = []
    return_dict = {}
    content = request.get_json()
    data = get_data(content)

    print(data)
    return jsonify(data)

if __name__ == "__main__":
    app.run()