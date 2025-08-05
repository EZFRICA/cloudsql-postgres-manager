# Use official Python image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy dependency files
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN adduser --disabled-password --gecos "" myuser

# Copy the rest of the application code
COPY . .

# Change ownership to non-root user
RUN chown -R myuser:myuser /app

# Switch to non-root user
USER myuser

# Expose the port used by Flask
EXPOSE 8080

# Command to start the Flask application with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:8080", "main:app"] 