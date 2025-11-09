#!/bin/bash
DEBUG=$1
PORT=8000
HOST=localhost
echo "${DEBUG}" = "DEBUG"
if [ "${DEBUG}" = "DEBUG" ]; then
    export DEBUG_BACKEND='DEBUG'
    echo "Debug mode enabled"
     DEBUG_ENABLED="python -m debugpy --listen 127.0.0.1:5679 --wait-for-client -m "
else
    RELOAD="--reload"
fi
echo "PYTHONPATH=./src ${DEBUG_ENABLED} uvicorn wulfs_routing_api.main:app ${RELOAD} --host ${HOST} --port ${PORT}"
PYTHONPATH=./src ${DEBUG_ENABLED} uvicorn wulfs_routing_api.main:app ${RELOAD} --host ${HOST} --port ${PORT}
