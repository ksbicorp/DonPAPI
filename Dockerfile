FROM python:3.11-slim
LABEL org.midas.tool="DonPAPI"
WORKDIR /opt/tool

# Install system dependencies (git might be needed for pip install git+)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install MCP dependencies and DonPAPI
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP server
COPY mcp_server.py .

# Environment
ENV DONPAPI_OUTPUT="/root/.donpapi/loot"
ENV DONPAPI_GUI_PORT="8088"

# Create output directory
RUN mkdir -p /root/.donpapi/loot

EXPOSE 8088

CMD ["python", "mcp_server.py"]
