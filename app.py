from flask import Flask, request, jsonify
import json
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
CORS(app)

db = SQLAlchemy(app)

class WEBM(db.Model):
    __tablename__ =  'webms'
    id = db.Column(db.Integer, primary_key=True)
    md5 = db.Column(db.String(150), unique=True, nullable=False)
    screamer_chance = db.Column(db.Float, unique=False, nullable=False)
    
    def __init__(self, md5=None, screamer_chance=None):
        self.md5 = md5
        self.screamer_chance = screamer_chance

from detector import get_data    

@app.route("/api/", methods=['GET', 'POST'])
def hello():
    jobs = []
    return_dict = {}
    content = request.get_json()
    data = WEBM.query.filter_by(md5=content['md5']).first()
    if (data is None):
        data = get_data(content)


    print(data)
    return jsonify(data)

if __name__ == "__main__":
    app.run()