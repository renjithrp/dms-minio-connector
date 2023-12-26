from flask import Flask, request, jsonify
from storage import Storage
from common_utils import ping, get_unique_19_digit_id, json_response
from redis_utils import get_redis_connection
from prometheus_client import start_http_server

storage = Storage()
app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

@app.before_request
def init_redis():
    get_redis_connection()
@app.before_request
def init_storage():
    storage.initialize_client()

# Endpoint to handle binary data upload
@app.route('/dss/api/put/<tenant_id>', methods=['GET', 'POST', 'PUT'])
def upload_binary_data(tenant_id):
    if 'bin' not in request.files:
        print("error")
        return jsonify({'error': 'No data part'}), 400
    binary_data = request.files['bin'].read()
    tags = {"tenant_id": tenant_id}
    file_id = get_unique_19_digit_id()
    if file_id is None:
        return json_response({"error":True,"errorCode":1,"data":{"cid":f"{file_id}"}})
    storage.initialize_client()
    return storage.upload_file(file_id, binary_data, tags=tags)

@app.route('/dss/api/ping', methods=['GET'])
def ping_check():
    return ping()


@app.route('/dss/api/stats/<file_id>', methods=['GET'])
def stats(file_id):
    storage.initialize_client()
    return storage.get_stats(file_id)    

@app.route('/dss/api/get/<file_id>', methods=['GET'])
def get_pdf_file(file_id):
    storage.initialize_client()
    return storage.download_file(file_id)

@app.route('/dss/api/getimage/<file_id>/<int:page_number>', methods=['GET'])
def get_pdf_image(file_id, page_number):
    scale = float(request.args.get('scale', 1.0))
    if scale > 2:
        scale = float(2)
    storage.initialize_client()
    return storage.get_pdf_image(file_id, page_number=page_number, scale=scale)

@app.route('/metrics')
def metrics():
    from prometheus_client import generate_latest
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4'}
if __name__ == '__main__':
    app.run(debug=True, port=9082, host="0.0.0.0")