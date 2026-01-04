FROM python:3.11-slim

WORKDIR /app

# Kopiuj requirements i instaluj zależności
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiuj kod aplikacji
COPY app/ ./app/

# Expose port 8080
EXPOSE 8080

# Uruchom Streamlit
CMD ["streamlit", "run", "app/app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
