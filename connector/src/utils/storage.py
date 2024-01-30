from utils.minio import connect_minio, put_object, create_tags, get_tags, get_object_stream, upload_object_with_retention
from io import BytesIO
import os
import PyPDF2
from flask import  send_file
from pdf2image import convert_from_bytes
from utils.common import file_response, json_response
from flask import current_app
from metrics import * 
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
from pdf2image import convert_from_bytes, convert_from_path
from docx2pdf import convert
from docx import Document
from spire.doc import Document as SpireDocument, ImageType
from utils.convert import convert_to_pdf_soffice

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
        print("upload-started")
        error = put_object(self.client, self.bucket_name, object_name, data, tags)
        print("upload-started")
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
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                page_length = self.get_doc_page_count(file_id, stream)

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
        
        if images:
            image = images[0].resize((int(images[0].width * scale), int(images[0].height * scale)))
            image_stream = BytesIO()
            image.save(image_stream, 'JPEG', quality=40, optimize=True)
            image_stream.seek(0)
            return image_stream
        else:
            return None

    def create_cache_image(self, redis_client, minio_client, cache_bucket_name, object_name, data, content_type):
        if redis_client is None:
            print("Redis connection error")
            return

        try:
            lock_acquired = redis_client.set(object_name, 'lock_value', nx=True, px=35000)  # Lock expires in 35 seconds
        except Exception as e:
            print(f"Redis set lock failed for cache job, {object_name}: {e}")
            return

        if lock_acquired:
            try:
                print("Creating cache image")
                upload_object_with_retention(minio_client, cache_bucket_name, object_name, data, content_type)
            finally:
                redis_client.delete(object_name)

    def calculate_size_kb(self, image):
        with BytesIO() as temp_stream:
            image.save(temp_stream, format='JPEG', quality=100, optimize=True)
            size_kb = len(temp_stream.getvalue()) / 1024
        return size_kb

    def calculate_optimal_quality(self, image, target_size_kb, current_size_kb):
        if current_size_kb <= target_size_kb:
            return 100  # No need to reduce quality

        quality = int((target_size_kb / current_size_kb) * 100)
        return max(min(quality, 95), 1)  # Ensure quality is between 1 and 95

    def get_content_preview(self, file_id, page_number=1, scale=1.4):
        cache_image_file = f'{file_id}_page_{page_number}.jpeg'
        
        with current_app.app_context():
            redis_client = current_app.config['redis']

            try:
                cache_stream, content_type, _ = get_object_stream(self.client, self.cache_bucket_name, cache_image_file, BytesIO())
                cache_stream.seek(0)

                if cache_stream:
                    print("From cache")
                    return send_file(cache_stream, mimetype='image/jpeg', download_name=cache_image_file)
            except Exception as cache_exception:
                print(f"Error checking cache: {cache_exception}")

            print("Not from cache")
            stream, content_type, _ = get_object_stream(self.client, self.bucket_name, file_id, BytesIO())
            stream.seek(0)
            print(content_type)
            if content_type == 'application/pdf':
                return self.process_pdf(redis_client, file_id, cache_image_file, stream, page_number, scale)
            elif content_type.startswith('image/'):
                return self.process_image(redis_client, file_id, self.cache_bucket_name, cache_image_file, stream, content_type)
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                return self.process_doc_page(redis_client, file_id, stream, scale=scale, page_number=page_number)
            else:
                return None

    def process_pdf(self, redis_client, file_id, cache_image_file, stream, page_number, scale):
        image_stream = self.pdf_stream_to_image(stream, page_number, scale=scale)

        if image_stream:
            get_pdf_image_success_counter.labels(bucket_name=self.bucket_name).inc()
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self.create_cache_image, redis_client, self.client, self.cache_bucket_name, cache_image_file, image_stream.getvalue(), 'image/jpeg')

            return send_file(image_stream, mimetype='image/jpeg', download_name=cache_image_file)
        else:
            get_pdf_image_fail_counter.labels(file_id=file_id, bucket_name=self.bucket_name).inc()
            return None
        
    def process_image(self, redis_client, file_id, cache_bucket_name, cache_image_file, stream, content_type):
        try:
            print("No cache")
            with Image.open(stream) as image:
                rgb = image.convert("RGB")
                output_stream = BytesIO()

                # Adjust quality based on the desired size
                target_size_kb = 1024  # Set your target size in kilobytes
                current_size_kb = self.calculate_size_kb(rgb)
                quality = self.calculate_optimal_quality(rgb, target_size_kb, current_size_kb)
                print("Quality:", quality)

                rgb.save(output_stream, format='JPEG', quality=quality, optimize=True)
                output_stream.seek(0)

                with ThreadPoolExecutor() as executor:
                    future = executor.submit(self.create_cache_image, redis_client, self.client, cache_bucket_name, cache_image_file, output_stream.getvalue(), content_type)

                return send_file(output_stream, mimetype=content_type, download_name=f'{file_id}')
        except Exception as e:
            print(f"Error: {e}")
            return send_file(stream, mimetype=content_type, download_name=f'{file_id}')
        
    def get_doc_page_count(self, file_id, stream):
        try:
            print(f"Processing DOC")
            temp_file_path = f"{file_id}.docx"
            if not os.path.exists(temp_file_path):
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(stream.getvalue())
            pdf_file = convert_to_pdf_soffice(temp_file_path)
            with open(pdf_file, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
            return num_pages
        except Exception as e:
            Exception(f"Error reading PDF file page count: {e}")
        
    def process_doc_page(self, redis_client, file_id, stream, scale=1.4, page_number=1):
        try:
            print(f"Processing DOC")
            temp_file_path = f"{file_id}.docx"
            if not os.path.exists(temp_file_path):
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(stream.getvalue())
            pdf_file = convert_to_pdf_soffice(temp_file_path)
            if pdf_file:
                try:
                    images = convert_from_path(pdf_file)
                except Exception as e:
                    raise Exception(f"Error in conversion: {e}")
                for i, image in enumerate(images):
                    current_page = i + 1
                    resized_image = image.resize((int(image.width * scale), int(image.height * scale)))
                    image_stream = BytesIO()
                    resized_image.save(image_stream, 'JPEG', quality=40, optimize=True)
                    image_stream.seek(0)
                    resized_cache_image_file = f'{file_id}_page_{current_page}.jpeg'
                    if current_page == page_number:
                        image_to_return = image_stream
                        cache_image_file = resized_cache_image_file
                    #self.create_cache_image(redis_client, self.client, self.cache_bucket_name, resized_cache_image_file, image_stream.getvalue(), 'image/jpeg')
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(self.create_cache_image, redis_client, self.client, self.cache_bucket_name, resized_cache_image_file, image_stream.getvalue(), 'image/jpeg')
                        
                return send_file(image_to_return, mimetype='image/jpeg', download_name=cache_image_file)
        except Exception as e:
            print(f"Error processing DOC")
            return None