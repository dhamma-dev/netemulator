# NetEmulator Deployment Guide

This guide covers deploying NetEmulator for production use.

## System Requirements

### Hardware
- **CPU**: 8+ cores recommended (scales with topology size)
- **RAM**: 16GB minimum, 32GB+ recommended
- **Storage**: 50GB+ for logs and metrics
- **Network**: 10Gbps NIC recommended for high-throughput scenarios

### Software
- **OS**: Ubuntu 20.04 LTS or 22.04 LTS (other Linux distros may work)
- **Kernel**: 5.4+ (for modern tc/netem features)
- **Python**: 3.9+
- **Privileges**: Root access required for network operations

## Installation

### Quick Install

```bash
# Clone repository
git clone https://github.com/appneta/netemulator.git
cd netemulator

# Run installer (requires sudo)
sudo make install

# Activate virtual environment
source venv/bin/activate
```

### Manual Installation

See `scripts/install_dependencies.sh` for detailed steps.

## Configuration

### System Tuning

Edit `/etc/sysctl.d/99-netemulator.conf`:

```
# IP forwarding
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1

# Network buffers
net.core.rmem_max=134217728
net.core.wmem_max=134217728
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864

# Queue discipline
net.core.default_qdisc=fq_codel
net.ipv4.tcp_congestion_control=bbr

# Increase max connections
net.core.somaxconn=8192
net.ipv4.tcp_max_syn_backlog=8192
```

Apply:
```bash
sudo sysctl -p /etc/sysctl.d/99-netemulator.conf
```

### FRRouting Configuration

Enable daemons in `/etc/frr/daemons`:
```
zebra=yes
bgpd=yes
ospfd=yes
```

Restart FRR:
```bash
sudo systemctl restart frr
```

## Running NetEmulator

### Development Mode

```bash
# Start services
make start

# View logs
tail -f logs/api.log

# Stop services
make stop
```

### Production Mode

Use systemd for service management.

Create `/etc/systemd/system/netemulator-api.service`:

```ini
[Unit]
Description=NetEmulator API Service
After=network.target

[Service]
Type=simple
User=netemulator
Group=netemulator
WorkingDirectory=/opt/netemulator
Environment="PATH=/opt/netemulator/venv/bin"
ExecStart=/opt/netemulator/venv/bin/python3 -m netemulator.control.api
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable netemulator-api
sudo systemctl start netemulator-api
```

## Monitoring

### Prometheus

Configure Prometheus to scrape metrics:

```yaml
scrape_configs:
  - job_name: 'netemulator'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/api/v1/metrics'
    scrape_interval: 5s
```

### Grafana

Import dashboards from `dashboards/` directory:

```bash
python3 -m netemulator.observability.dashboard
```

Access Grafana at `http://localhost:3000`

### Logging

Logs are written to:
- API: `logs/api.log`
- Scheduler: `logs/scheduler.log`
- System: `journalctl -u netemulator-api`

Use log aggregation (ELK, Loki) for production.

## Security

### Network Isolation

- Run in isolated network namespace
- Use firewall rules to restrict access
- Limit WireGuard to known IPs

Example iptables rules:
```bash
# Allow API only from management network
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -j DROP

# Allow WireGuard
iptables -A INPUT -p udp --dport 51820 -j ACCEPT
```

### Authentication

For production, add authentication to the API:
- Use OAuth2/OIDC
- Implement API keys
- Add RBAC for multi-tenant use

### TLS

Use reverse proxy (nginx, traefik) with TLS:

```nginx
server {
    listen 443 ssl http2;
    server_name netemulator.example.com;
    
    ssl_certificate /etc/ssl/certs/netemulator.crt;
    ssl_certificate_key /etc/ssl/private/netemulator.key;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Backup and Recovery

### Topology Definitions

Store YAML files in version control (git):
```bash
git init topologies
cp examples/*.yaml topologies/
cd topologies && git add . && git commit -m "Initial topologies"
```

### Metrics Data

Backup Prometheus data:
```bash
# Stop Prometheus
sudo systemctl stop prometheus

# Backup data directory
tar czf prometheus-backup-$(date +%Y%m%d).tar.gz /var/lib/prometheus/

# Restart Prometheus
sudo systemctl start prometheus
```

### Event Logs

Archive old logs:
```bash
# Compress and archive logs older than 7 days
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

## Scaling

### Horizontal Scaling

Run multiple NetEmulator instances:

1. **Per-region deployment**: One instance per geographic region
2. **Per-tenant deployment**: Isolated instances per customer
3. **Load-balanced API**: Multiple API servers behind load balancer

### Vertical Scaling

- Increase CPU: More cores = more concurrent topologies
- Increase RAM: Larger topologies with more nodes
- Faster storage: SSD for metrics and logs

### Resource Quotas

Limit resources per topology in `config.yaml`:

```yaml
resource_limits:
  max_nodes_per_topology: 200
  max_links_per_topology: 500
  max_concurrent_topologies: 5
  cpu_shares_per_topology: 2048
  memory_limit_per_topology: 4g
```

## Troubleshooting

### Common Issues

**Issue: Mininet fails to start**
```bash
# Clean up stale Mininet state
sudo mn -c

# Check for conflicting processes
ps aux | grep python
```

**Issue: High packet loss in emulation**
```bash
# Check CPU usage
top

# Increase buffer sizes
sudo sysctl -w net.core.netdev_max_backlog=5000

# Check for dropped packets
tc -s qdisc show
```

**Issue: FRR daemons not starting**
```bash
# Check logs
sudo tail -f /var/log/frr/frr.log

# Verify configuration
sudo vtysh -c "show run"

# Restart daemons
sudo systemctl restart frr
```

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python3 -m netemulator.control.api
```

### Performance Profiling

Profile the API:
```bash
python3 -m cProfile -o api.prof -m netemulator.control.api
python3 -m pstats api.prof
```

## Maintenance

### Regular Tasks

**Daily**:
- Monitor metrics and alerts
- Check for failed scenarios
- Review error logs

**Weekly**:
- Archive old logs
- Review resource usage
- Update topology definitions

**Monthly**:
- Update system packages
- Review security patches
- Backup configurations

### Updates

Update NetEmulator:
```bash
cd /opt/netemulator
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart netemulator-api
```

## Support

- **Documentation**: See README.md and CONTRIBUTING.md
- **Issues**: File bugs on GitHub
- **Community**: Join our Slack channel
- **Commercial**: Contact AppNeta support

