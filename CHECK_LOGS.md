# How to Find DNS Server Logs

The DNS server uses `print()` statements for logging. The log location depends on how it's running:

## Common Scenarios

### 1. Running as a systemd service
```bash
# Check service status
sudo systemctl status dns-server

# View logs
sudo journalctl -u dns-server -f

# View recent logs
sudo journalctl -u dns-server -n 100
```

### 2. Running with nohup
```bash
# Check for nohup.out in the directory where you started it
ls -la nohup.out
tail -f nohup.out
```

### 3. Running in a screen/tmux session
```bash
# List screen sessions
screen -ls

# Attach to the session
screen -r <session_name>

# Or check tmux
tmux ls
tmux attach -t <session_name>
```

### 4. Running as a background process
```bash
# Find the process
ps aux | grep dns_server

# Check if output was redirected
# Look for commands like: python3 dns_server.py > /var/log/dns.log 2>&1 &
```

### 5. Running directly
If you started it with `python3 dns_server.py`, the logs appear in that terminal.

## What to Look For

When you query the server, you should see debug output like:
```
Query: domain=securityprox.net., normalized=securityprox.net, config=securityprox.net, qtype=6
SOA query for securityprox.net
```

Or if there's a mismatch:
```
Query: domain=securityprox.net., normalized=securityprox.net, config=dynspark.911cellular.com, qtype=6
Domain mismatch: securityprox.net does not match dynspark.911cellular.com
```

## Quick Check Commands

```bash
# Check if process is running
ps aux | grep dns_server

# Check systemd services
systemctl list-units | grep dns

# Check for log files
find /var/log -name "*dns*" 2>/dev/null
find /home -name "nohup.out" 2>/dev/null
find /opt -name "*dns*.log" 2>/dev/null
```

