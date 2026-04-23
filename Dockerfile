FROM python:3.12-slim

WORKDIR /app

# Install deps first (layer-cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY api/   api/
COPY src/   src/
COPY tests/ tests/

# Persist user data outside the container via volume mount
RUN mkdir -p api/data

EXPOSE 8005

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8005"]
