# ITU-T Report Generator - Hugging Face Spaces Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY web-app/ ./web-app/
COPY scripts-new/ ./scripts-new/
COPY wp_doc_template/ ./wp_doc_template/
COPY question_doc_template/ ./question_doc_template/

# Create temp directory for generated reports
RUN mkdir -p /app/web-app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=web-app/app.py

# Expose port for Hugging Face Spaces (must be 7860)
EXPOSE 7860

# Run the application
CMD ["python", "-c", "import sys; sys.path.insert(0, 'web-app'); from app import app; app.run(host='0.0.0.0', port=7860)"]
