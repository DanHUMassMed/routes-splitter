#/bin/bash
cd frontend
PYTHONPATH=./src streamlit run ./src/wulfs_routing_web/app.py --server.port 8080 --server.address 0.0.0.0