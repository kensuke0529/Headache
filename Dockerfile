FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY fetch_headache_data.py .
COPY templates/ templates/
COPY static/ static/

# Expose port (Render will set PORT env var)
EXPOSE ${PORT:-5000}

# Run the app (use PORT env var if available, default to 5000)
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --timeout 120 app:app

