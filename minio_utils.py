from minio import Minio
import io
from minio.commonconfig import Tags
from io import BytesIO  
from flask import current_app
from metrics import minio_connection_fail_counter, minio_upload_fail_counter, minio_upload_success_counter, minio_get_stream_fail_counter, minio_get_stream_success_counter
def connect_minio():
    try:
        minio_client = Minio(
        current_app.config.get('MINIO_SERVER'),
        access_key=current_app.config.get('MINIO_ACCESS_KEY'),
        secret_key=current_app.config.get('MINIO_SECRET_KEY'),
        secure=current_app.config.get('MINIO_SECURE', False)
    )
        current_app.extensions['minio_client'] = minio_client
        return current_app.extensions['minio_client']
    except Exception as e:
        minio_connection_fail_counter.inc()
        server = current_app.config.get('MINIO_SERVER')
        raise ConnectionError(f'Unable to connect to minio {server}, exception: {e}')
    
def put_object(client, bucket_name, object_name, data, tags=None):
    if tags is None:
        tags = {}
    try:
        # Check if bucket exists, create if not
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        # Check if the object already exists
        try:
            client.stat_object(bucket_name, object_name)
            error_message = f"minio object '{object_name}' already exists in bucket '{bucket_name}'"
            return error_message
        except:
            pass

        # Upload the object
        data_stream = io.BytesIO(data)
        client.put_object(bucket_name, object_name, data_stream, len(data))

        # Set object tags
        create_tags(client, bucket_name, object_name, tags)
        minio_upload_success_counter.labels(bucket_name=bucket_name).inc()
        return None

    except Exception as e:
        minio_upload_fail_counter.labels(bucket_name=bucket_name).inc()
        create_tags(client, bucket_name, object_name, {"failed": True})
        error_message = f"minio object '{object_name}' upload failed '{bucket_name}': {str(e)}"
        return error_message
    
def get_object(client, bucket_name, object_name, local_file_path):
    try:
        client.fget_object(bucket_name, object_name, local_file_path)
        return None
    except Exception as e:
        return f"minio object '{object_name}' download failed from '{bucket_name}': {str(e)}"

def create_tags(client, bucket_name, object_name, tags):
    minio_tags = Tags.new_object_tags()
    for key, value in tags.items():
            minio_tags[key] = value
    client.set_object_tags(bucket_name, object_name, minio_tags)
    
def get_tags(client, bucket_name, object_name):
    try:
        tags = client.get_object_tags(bucket_name, object_name)
        return tags if tags is not None else {}
    except Exception as e:
        return {}
    
def get_object_stream(client, bucket_name, object_name, stream):
    try:
        obj = client.get_object(bucket_name, object_name)
        stream = BytesIO()
        for data in obj.stream(32*1024):  # Adjust the chunk size if needed
            stream.write(data)
        minio_get_stream_success_counter.labels(bucket_name=bucket_name).inc()
        return stream, None
    except Exception as e:
        minio_get_stream_fail_counter.labels(bucket_name=bucket_name, object_name=object_name).inc()
        return None,  f"minio object '{object_name}' get_object_stream '{bucket_name}': {str(e)}"
