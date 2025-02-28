# Use a lightweight base image with Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the application code
COPY fileOrganiser.py .

# Add a non-root user for better security
# RUN useradd -ms /bin/bash appuser && chown -R appuser /app
# USER appuser

# Use CMD instead of ENTRYPOINT for flexibility
CMD ["python", "fileOrganiser.py"]
