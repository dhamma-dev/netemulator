# Dockerfile for NetEmulator
# Note: Requires privileged mode for network operations

FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    openvswitch-switch \
    wireguard \
    wireguard-tools \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Mininet
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y mininet && \
    rm -rf /var/lib/apt/lists/*

# Install FRRouting
RUN curl -s https://deb.frrouting.org/frr/keys.asc | apt-key add - && \
    echo "deb https://deb.frrouting.org/frr jammy frr-stable" > /etc/apt/sources.list.d/frr.list && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y frr frr-pythontools && \
    rm -rf /var/lib/apt/lists/*

# Enable FRR daemons
RUN sed -i 's/^bgpd=no/bgpd=yes/' /etc/frr/daemons && \
    sed -i 's/^ospfd=no/ospfd=yes/' /etc/frr/daemons

# Set up application
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY netemulator/ ./netemulator/
COPY setup.py .
COPY README.md .

# Install application
RUN pip3 install -e .

# Configure system
RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf && \
    echo "net.ipv6.conf.all.forwarding=1" >> /etc/sysctl.conf

# Create directories
RUN mkdir -p /app/logs /app/topologies

# Expose API port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Start API server
CMD ["python3", "-m", "netemulator.control.api"]

