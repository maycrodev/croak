FROM python:3.11-slim

WORKDIR /app

# 1) Dependencias del servicio (capa cacheable).
COPY services/gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) Librerias compartidas + codigo del servicio.
COPY libs/ ./libs/
COPY services/gateway/ ./

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
