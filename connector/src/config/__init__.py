import os
class Config():
    # Minio configuration for development environment
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY')
    MINIO_SERVER = os.environ.get('MINIO_SERVER')
    MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME')
    # Redis configuration
    REDIS_SERVER = os.environ.get('REDIS_SERVER', '127.0.0.1')
    REDIS_PORT = os.environ.get('REDIS_PORT', 6379)
    # DMS configuration
    DMS_SERVER_NAME = os.environ.get('DMS_SERVER_NAME', 'A.1')
