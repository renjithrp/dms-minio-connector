from flask import jsonify, make_response
import requests
from utils.redis import initialize_redis_client
import time
from flask import current_app
from metrics import  redis_failure_counter, redis_duplicate_counter, ping_success_counter, ping_failure_counter

def json_response(data, code=200, headers=None):
    if headers is None:
        headers = {}
    response = make_response(jsonify(data), code)
    response.headers["Content-Type"] = "application/json;charset=ISO-8859-1"
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    return response

def file_response(data, code=200, headers=None):
    if headers is None:
        headers = {}
    response = make_response(data, code)
    response.headers["Content-Type"] = "application/json;charset=ISO-8859-1"
    if headers:
        for key, value in headers.items():
            response.headers[key] = value
    return response

def get_unique_19_digit_id():
    try:
        redis_client = initialize_redis_client()
    except Exception as e:
        print(f"Redis connection failed, get_unique_19_digit_id {e}")
        return None
    lock_key = 'unique_id_lock'
    unique_id_key = 'unique_id'

    # Acquire a lock using Redis's SET command with NX (not exists) and PX (expiration time in milliseconds)
    try:
        lock_acquired = redis_client.set(lock_key, 'lock_value', nx=True, px=5000)  # Lock expires in 5 seconds
    except Exception as e:
        redis_failure_counter.inc()
        print(f"Redis set lock failed, get_unique_19_digit_id {e}")
        return None

    if lock_acquired:
        try:
            # Get the last stored unique ID or start from 0 if it doesn't exist
            last_id = int(redis_client.get(unique_id_key) or 0)

            # Generate a new unique ID
            seconds = int(time.time())
            nanoseconds = int(time.time_ns() % 1000000000)
            unique_id = int(f"{seconds}{nanoseconds:09d}")

            # Check if the generated ID is greater than the last stored ID, then store it
            if unique_id > last_id:
                redis_client.set(unique_id_key, unique_id)
                return unique_id
            else:
                # If generated ID is not greater, increment the last stored ID
                last_id += 1
                redis_client.set(unique_id_key, last_id)
                return last_id
        finally:
            # Release the lock
            redis_client.delete(lock_key)
    else:
        # Lock was not acquired, handle accordingly (e.g., retry or return an error)
        redis_duplicate_counter.inc()
        return None

def ping(url=None):
    host = current_app.config.get('MINIO_SERVER')
    secure = current_app.config.get('MINIO_SECURE', False)
    scheme = 'http'
    if secure:
        scheme = 'https'
    server_name = current_app.config.get('DMS_SERVER_NAME')
    if url is None:
        url = f"{scheme}://{host}/minio/health/live"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            ping_success_counter.inc()  # Increment success count metric
            return json_response({"error": False, "errorCode": 0, "msg": "!DSS", "data": {"server_name": server_name}})
        else:
            ping_failure_counter.inc()  # Increment failure count metric
            print(f"Server {url} responded with status code: {response.status_code}")
            return json_response({"error": True, "errorCode": 1, "msg": "!DSS", "data": {"server_name": server_name}})
    except requests.RequestException as e:
        ping_failure_counter.inc()  # Increment failure count metric
        print(f"Failed to connect to MinIO: {e}")
        return json_response({"error": True, "errorCode": 1, "msg": "!DSS", "data": {"server_name": server_name}})