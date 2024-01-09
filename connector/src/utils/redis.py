from flask import current_app
import redis
from rq import Queue

def initialize_redis_client():
    try:
        if 'redis' not in current_app.config:
            current_app.config['redis'] = redis.StrictRedis(
                host=current_app.config.get('REDIS_SERVER', 'localhost'),
                port=current_app.config.get('REDIS_PORT', 6379),
                db=current_app.config.get('REDIS_DB', 0)
            )
        return current_app.config['redis']
    except Exception as e:
        print(f"Failed to connect to redis {e}")

def initialize_redis_queue():
    try:
        if 'queue' not in current_app.config:
            current_app.config['queue'] = Queue(connection=current_app.config['redis'])
        return current_app.config['queue']
    except Exception as e:
         print(f"Failed to connect to redis {e}")
