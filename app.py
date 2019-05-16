from flask import Flask, request, jsonify
import json
from flask_cors import CORS, cross_origin
from flask_pymongo import PyMongo
import os


app = Flask(__name__)
app.config["MONGO_URI"] = os.environ.get('DATABASE_URL')
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


mongo = PyMongo(app)

from detector import get_data    

@app.route("/api/", methods=['POST'])
@cross_origin()
def hello():
    content = request.get_json()
    webm = None
    webm = mongo.db.webms.find_one({'md5': content['md5']})
    if (webm is None):
        data = get_data(content)
        webm = {'md5': data['md5'], 'screamer_chance': data['scream_chance']}
        mongo.db.webms.insert_one(webm)
    else:
        data = {}
        data["md5"] = webm['md5']
        data["scream_chance"] = webm['screamer_chance']

    print(jsonify(data))
    return jsonify(data)

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

if __name__ == "__main__":
    app.run()