FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/storage
ENV SUPERADMIN_EMAIL=direzione@serrastudio.it
ENV APP_BASE_URL=https://cantina.187.126.30.207.sslip.io

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/storage

EXPOSE 8501

CMD ["streamlit", "run", "cantina_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--server.enableStaticServing=true"]
