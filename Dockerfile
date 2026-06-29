FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Command to run both services
CMD ["python", "run.py"]
