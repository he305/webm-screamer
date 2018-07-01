from flask import Flask, request
from detector import get_data
import json
import multiprocessing
from flask import jsonify


app = Flask(__name__)
pool = None

@app.route("/api/", methods=['GET', 'POST'])
def hello():
    jobs = []
    return_dict = {}
    content = request.get_json()
    #pool = multiprocessing.Pool(processes = len(content))
    #data = pool.map(get_data, [url for url in content])
    data = get_data(content)
    #for data in content:
        #return_dict[data['md5']] = get_data(data['url'])

    
    print(data)
    return jsonify(data)
    # url = request.args.get('url')
    # return json.dumps(get_data(url))

if __name__ == "__main__":
    app.run()