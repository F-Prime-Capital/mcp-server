# F-Prime MCP Server Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd --gid 1000 fprime && \
    useradd --uid 1000 --gid fprime --shell /bin/bash --create-home fprime

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install .

# Copy application code
COPY src/ ./src/

# Change ownership to non-root user
RUN chown -R fprime:fprime /app

# Switch to non-root user
USER fprime

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "fprime_mcp.main:app", "--host", "0.0.0.0", "--port", "8000"]