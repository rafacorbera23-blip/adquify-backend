
# Python 3.11 Slim Image
FROM python:3.11-slim

# Set environment
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Install system dependencies (needed for ReportLab, etc)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy App Code
COPY . .

# Create directory for data/pdfs
RUN mkdir -p data/generated_pdfs && chmod 777 data/generated_pdfs
RUN mkdir -p data/raw && chmod 777 data/raw

# Expose port
ENV PORT=8080
EXPOSE 8080

# Run
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
