FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ray_app ./ray_app

# Expose UDP ports for discovery and game state updates
EXPOSE 37020/udp
EXPOSE 6809/udp

# Command to run the UDP service
CMD ["python", "-m", "ray_app.udp_service"]
