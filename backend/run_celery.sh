#/bin/bash
PYTHONPATH=./src celery -A wulfs_routing_api.celery_app worker --concurrency=4 --loglevel=info

# After starting celery you can check if your tasks are registered with the below command
#PYTHONPATH=./src celery -A wulfs_routing_api.celery_app inspect registered