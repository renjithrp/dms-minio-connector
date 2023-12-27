class Config:
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    # Minio configuration for development environment
    MINIO_ACCESS_KEY='' # Minio user name / access key
    MINIO_SECRET_KEY='' # Minio user password / secret key
    MINIO_SERVER='' # Minio server url in <hostname:port> format
    MINIO_BUCKET_NAME='' # Update with the bucket name
    # Redis configuration
    REDIS_SERVER='' # Redis server address
    REDIS_PORT=6379
    DMS_SERVER_NAME='A.1' # DMS Server name / ID

class ProductionConfig(Config):
    MINIO_ACCESS_KEY=''
    MINIO_ACCESS_SECRET=''
    MINIO_SERVER=''