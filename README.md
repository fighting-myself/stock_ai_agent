

uvicorn main:app --reload --host 0.0.0.0 --port 8000

streamlit run frontend.py --server.port 6006 --server.address 0.0.0.0
