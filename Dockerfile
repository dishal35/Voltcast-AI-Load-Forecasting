# Voltcast-AI Load Forecasting API
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY req.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r req.txt

# Copy application code
COPY api/ ./api/
COPY artifacts/ ./artifacts/
COPY scripts/ ./scripts/
COPY workers/ ./workers/
COPY run_api.py .
COPY .env.example .env

# Copy database (if exists) - optional for development
COPY demand_forecast.db* ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# Run application
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
