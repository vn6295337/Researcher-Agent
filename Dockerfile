FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY mcp_client.py .
COPY configs/ ./configs/
COPY utils/ ./utils/
COPY mcp-servers/ ./mcp-servers/

# HuggingFace Spaces uses port 7860
EXPOSE 7860

# Run the A2A server
CMD ["python", "app.py"]
