FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn prometheus-client psutil httpx
COPY base_service.py /app/base_service.py
CMD ["python", "-c", "from base_service import app; import uvicorn; import os; uvicorn.run(app, host='0.0.0.0', port=int(os.getenv('SERVICE_PORT', '8080')))"]
