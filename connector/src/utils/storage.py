from utils.minio import connect_minio, put_object, create_tags, get_tags, get_object_stream
from io import BytesIO
import PyPDF2
from flask import  send_file
from pdf2image import convert_from_bytes
from utils.common import file_response, json_response
from flask import current_app
from metrics import * 

class Storage:
    def __init__(self):
        self.client = None
    def initialize_client(self):
        self.bucket_name = current_app.config.get('MINIO_BUCKET_NAME')
        self.client = connect_minio()
        
    def upload_file(self, file_id, data, tags=None):
        object_name = f'{file_id}.pdf'
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
             file_upload_success_counter.labels(bucket_name=self.bucket_name).inc()
             return json_response({"error":False,"errorCode":0,"data":{"cid":f"{file_id}"}})
    def download_file(self, file_id):
        object_name = f'{file_id}.pdf'
        stream, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
        try:
            stream.seek(0)
            file_download_success_counter.labels(bucket_name=self.bucket_name).inc()
            return file_response(send_file(stream,
                         mimetype='application/pdf',
                         as_attachment=True,
                         download_name=file_id))
        except Exception as e:
            print(e)
            file_download_fail_counter.labels(file_id=file_id,bucket_name=self.bucket_name).inc()
            return None
    def get_stats(self, file_id):
        object_name = f'{file_id}.pdf'
        tags = get_tags(self.client, self.bucket_name, object_name)
        stream, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
    
        try:
            stream.seek(0)
            file_size = stream.getbuffer().nbytes
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
                "mime_type": "application/pdf",
                "name": f"{object_name}.pdf",
                "page_wise_get": "true",
                "parts_count": "3",
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
            get_stats_fail_counter.labels(file_id=file_id,bucket_name=self.bucket_name).inc()
            return json_response(error_data, 202)
        
    def get_pdf_image(self, file_id, page_number=1, scale=1.4):
        object_name = f'{file_id}.pdf'
        stream, _ = get_object_stream(self.client, self.bucket_name, object_name, BytesIO())
        stream.seek(0)
        images = convert_from_bytes(stream.read(), first_page=page_number, last_page=page_number)  
        image_stream = BytesIO() 
        if images:
            new_width = int(images[0].width * scale)
            new_height = int(images[0].height * scale)
            images[0] = images[0].resize((new_width, new_height))
            images[0].save(image_stream, 'PNG')
            image_stream.seek(0)
            get_pdf_image_success_counter.labels(bucket_name=self.bucket_name).inc()
            return send_file(image_stream, mimetype='image/png',download_name=f'{file_id}_page_{page_number}.png')
        else:
            get_pdf_image_fail_counter.labels(file_id=file_id, bucket_name = self.bucket_name).inc()
            return None