import os
import redis
from rq import Worker, Queue

listen = ['default']

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')

conn = redis.from_url(redis_url)

if __name__ == '__main__':
    queues_to_listen = [Queue(q_name, connection=conn) for q_name in listen]
    worker = Worker(queues_to_listen, connection=conn)

    print(f"Worker starting... Listening on queues: {{', '.join(listen)}}")
    worker.work()
