from utils.minio import connect_minio, put_object, create_tags, get_tags, get_object_stream, upload_object_with_retension, create_bucket_if_not_exists
from io import BytesIO
import PyPDF2
from flask import  send_file
from pdf2image import convert_from_bytes
from utils.common import file_response, json_response
from flask import current_app
from metrics import * 
import threading
from PIL import Image
from utils.redis import initialize_redis_client

class Storage:
    def __init__(self):
        self.client = None
    def initialize_client(self):
        self.bucket_name = current_app.config.get('MINIO_BUCKET_NAME')
        self.cache_bucket_name = f"{self.bucket_name}-cache"
        self.client = connect_minio()
        
    def upload_file(self, file_id, data, tags=None):
        object_name = f'{file_id}'
        if tags is None:
            tags = {}
        tags["deleted"] = "false"
        tags["content_status"] = "PROCESSED"
        error = put_object(self.client, self.bucket_name, object_name, data, tags)
        if error is not None:
            create_tags(self.client, self.bucket_name, object_name, {"deleted": "true"})
            print(error)
            file_upload_fail_counter.labels(file_id=file_id,bucket_name=self.bucket_name).inc()
            return json_response({"error":True,"errorCode":1,"data":{"cid":f"{file_id}"}})
        else:
             print("Success1")
             file_upload_success_counter.labels(bucket_name=self.bucket_name).inc()
             return json_response({"error":False,"errorCode":0,"data":{"cid":f"{file_id}"}})
    def download_file(self, file_id):
        object_name = f'{file_id}'
        stream, content_type, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
        print(content_type)
        try:
            stream.seek(0)
            file_download_success_counter.labels(bucket_name=self.bucket_name).inc()
            return file_response(send_file(stream,
                         mimetype=content_type,
                         as_attachment=True,
                         download_name=file_id))
        except Exception as e:
            print(e)
            file_download_fail_counter.labels(file_id=file_id,bucket_name=self.bucket_name).inc()
            return None
    def get_stats(self, file_id):
        object_name = f'{file_id}'
        tags = get_tags(self.client, self.bucket_name, object_name)
        stream, content_type, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
        page_length = 1
        print(content_type)
        try:
            stream.seek(0)
            file_size = stream.getbuffer().nbytes
            if content_type == 'application/pdf':
                pdf_reader = PyPDF2.PdfReader(stream)
                page_length = len(pdf_reader.pages)

            data = {
                "tenant_id": tags.get('tenant_id'),
                "cid": object_name,
                "deleted": tags.get('deleted'),
                "content_status": tags.get('content_status'),
                "size": file_size,
                "page_count": page_length,
                "replica_count": "0",
                "mime_type": content_type,
                "name": f"{object_name}",
                "page_wise_get": "true",
                "parts_count": "0",
                "time_stamp": "1703142821000",  # Need to modify
                "replica": "false"
            }

            response_data = {
                "error": False,
                "errorCode": 0,
                "data": data 
            }
            get_stats_success_counter.labels(bucket_name=self.bucket_name).inc()
            return json_response(response_data)

        except Exception as e:
            error_data = {
                "error": True,
                "errorCode": 1
            }
            print(e)
            get_stats_fail_counter.labels(object_name=file_id,bucket_name=self.bucket_name).inc()
            return json_response(error_data, 202)
        
    def pdf_stream_to_image(self, stream, page_number=1, scale=1.4):
        images = convert_from_bytes(stream.read(), first_page=page_number, last_page=page_number)  
        image_stream = BytesIO() 
        if images:
            new_width = int(images[0].width * scale)
            new_height = int(images[0].height * scale)
            images[0] = images[0].resize((new_width, new_height))
            images[0].save(image_stream, 'JPEG', quality=40,optimize=True)
            image_stream.seek(0)
            return image_stream
        else:
            return None
    def create_cache_image(self, object_name, data, content_type):
        try:
            redis_client = initialize_redis_client()
        except Exception as e:
            print(f"Redis connection failed, image cache lock {e}")
            return None
        try:
            lock_acquired = redis_client.set(object_name, 'lock_value', nx=True, px=35000)  # Lock expires in 5 seconds
        except Exception as e:
            print(f"Redis set lock failed for cache job,  {object_name} {e}")
            return None
        if lock_acquired:
            redis_client.set(object_name, True)
            try:
                upload_object_with_retension(self.client, self.cache_bucket_name, object_name, data, content_type)
            finally:
                redis_client.delete(object_name)

    def get_content_preview(self, file_id, page_number=1, scale=1.4):
        object_name = f'{file_id}'
        cache_image_file = f'{file_id}_page_{page_number}.jpeg'
        try:
            cache_stream, content_type, _ = get_object_stream(self.client, self.cache_bucket_name, cache_image_file, BytesIO())
            cache_stream.seek(0)

            if cache_stream:
                print("from cache")
                return send_file(cache_stream, mimetype='image/jpeg',download_name=cache_image_file)
        except:
            print("not from cache")
            pass
        stream, content_type, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
        stream.seek(0)
        if content_type == 'application/pdf':
            image_stream = self.pdf_stream_to_image(stream, page_number, scale=scale)
            if image_stream is not None:
                get_pdf_image_success_counter.labels(bucket_name=self.bucket_name).inc()
                file_upload_thread = threading.Thread(target=self.create_cache_image,  args=(cache_image_file, image_stream.getvalue(), content_type))
                file_upload_thread.start()
                return send_file(image_stream, mimetype='image/jpeg',download_name=cache_image_file)
            else: 
                get_pdf_image_fail_counter.labels(file_id=file_id, bucket_name = self.bucket_name).inc()
                return None
        elif content_type.startswith('image/'):
            try:
                print("no cache")
                image = Image.open(stream)
                output_stream = BytesIO()
                image.save(output_stream, format='JPEG', quality=40, optimize=True)
                output_stream.seek(0)
                file_upload_thread = threading.Thread(target=self.create_cache_image,  args=(cache_image_file, output_stream.getvalue(), content_type))
                file_upload_thread.start()
                return send_file(output_stream, mimetype=content_type,download_name=f'{file_id}')
            except:
                return send_file(stream, mimetype=content_type,download_name=f'{file_id}')
        else:
            return None