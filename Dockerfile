FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python3 -m app.generar_org
ENV PORT=8000
# Una sola instancia y un solo worker: el estado de la corrida vive en memoria y se comparte por SSE.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --proxy-headers"]
