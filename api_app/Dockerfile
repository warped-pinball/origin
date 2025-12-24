FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_app ./api_app

# Expose HTTP port for the API/web UI
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "api_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
