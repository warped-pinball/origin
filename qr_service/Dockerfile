FROM python:3.11-slim

RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY package.json ./
RUN npm install --production
COPY service ./service
COPY database.py models.py __init__.py ./
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000"]
