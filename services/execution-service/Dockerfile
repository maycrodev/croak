FROM python:3.11-slim

WORKDIR /app

# 1) Dependencias del servicio (capa cacheable).
COPY services/execution-service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Librerias compartidas (contract-first) + codigo del servicio.
COPY libs/ ./libs/
COPY services/execution-service/ ./

ENV PYTHONPATH=/app
EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]