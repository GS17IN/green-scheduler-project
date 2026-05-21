FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scheduler
COPY scheduler/green_scheduler.py .

# Run as non-root 
RUN useradd -m scheduler
USER scheduler

ENTRYPOINT ["python", "green_scheduler.py", "--in-cluster"]
