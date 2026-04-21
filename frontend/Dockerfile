FROM python:3.11-slim

WORKDIR /app

COPY frontend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY frontend /app/frontend

ENV BACKEND_URL=http://backend:8001

EXPOSE 6006

CMD ["streamlit", "run", "/app/frontend/app.py", "--server.port", "6006", "--server.address", "0.0.0.0"]
