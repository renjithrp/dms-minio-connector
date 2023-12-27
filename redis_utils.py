from flask import current_app
import redis

def get_redis_connection():
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