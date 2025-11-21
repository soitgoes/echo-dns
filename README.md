# Echo DNS Server

A simple DNS server that converts subdomain dashes to dots for IP addresses.  DOES not resolve addresses

## How it works

The server listens for DNS queries and converts subdomain patterns like:
- `192-168-1-1.somedomain.com` → `192.168.1.1`
- `10-0-0-1.somedomain.com` → `10.0.0.1`

## Features

- Configurable domain via JSON configuration file
- IP address validation (only valid IPv4 addresses are returned)
- Error responses for invalid IP addresses
- Static CNAME records (takes precedence over dynamic IP conversion)
- Configurable nameservers
- SOA and NS record support
- Simple UDP-based DNS server implementation

## Installation

1. Clone or download this repository
2. Ensure you have Python 3.6+ installed
3. No additional dependencies required (uses only standard library)

## Configuration

The server uses a `config.json` file for configuration. If the file doesn't exist, it will be created with default values:

```json
{
  "domain": "somedomain.com",
  "port": 53,
  "host": "0.0.0.0",
  "nameservers": ["ns1.somedomain.com", "ns2.somedomain.com"],
  "nameserver_ips": ["127.0.0.1", "127.0.0.1"],
  "cnames": {
    "www": "example.com",
    "mail": "mail.example.com"
  }
}
```

### Configuration Options

- `domain`: The domain that the server will respond to (default: "somedomain.com")
- `port`: The port to listen on (default: 53)
- `host`: The host address to bind to (default: "0.0.0.0")
- `nameservers`: List of nameserver hostnames for NS records (default: ["ns1.{domain}", "ns2.{domain}"])
- `nameserver_ips`: List of IP addresses for nameserver A records (default: ["127.0.0.1", "127.0.0.1"])
- `cnames`: Dictionary of static CNAME records (takes precedence over dynamic IP conversion)
  - Key can be subdomain (e.g., "www") or full domain (e.g., "www.somedomain.com")
  - Value is the CNAME target (e.g., "example.com")

## Usage

### Running the server

```bash
python3 dns_server.py
```

### Testing with dig

```bash
# Test a valid IP conversion
dig @localhost 192-168-1-1.somedomain.com

# Test an invalid IP (should return NXDOMAIN)
dig @localhost 999-999-999-999.somedomain.com
```

### Testing with nslookup

```bash
# Test a valid IP conversion
nslookup 192-168-1-1.somedomain.com localhost

# Test an invalid IP (should return NXDOMAIN)
nslookup 999-999-999-999.somedomain.com localhost
```

## Examples

### Dynamic IP Conversion

| Query | Result |
|-------|--------|
| `192-168-1-1.somedomain.com` | `192.168.1.1` |
| `10-0-0-1.somedomain.com` | `10.0.0.1` |
| `8-8-8-8.somedomain.com` | `8.8.8.8` |
| `999-999-999-999.somedomain.com` | NXDOMAIN (invalid IP) |
| `not-an-ip.somedomain.com` | NXDOMAIN (invalid IP) |
| `192-168-1-1.otherdomain.com` | NXDOMAIN (wrong domain) |

### Static CNAME Records (Takes Precedence)

If configured with:
```json
{
  "cnames": {
    "www": "example.com",
    "api": "api.example.com"
  }
}
```

| Query | Result |
|-------|--------|
| `www.somedomain.com` | CNAME to `example.com` |
| `api.somedomain.com` | CNAME to `api.example.com` |
| `192-168-1-1.somedomain.com` | `192.168.1.1` (dynamic IP conversion) |

**Note:** CNAME records take precedence over dynamic IP conversion. If a CNAME is configured for a subdomain, it will be returned instead of attempting IP conversion.

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Notes

- The server runs on port 53 by default, which requires root privileges on most systems
- To run without root privileges, change the port in the configuration file
- The server handles A record queries (IPv4 addresses) and CNAME records
- Static CNAME records take precedence over dynamic IP conversion
- Invalid IP addresses return NXDOMAIN responses
- Supports SOA and NS queries for proper DNS delegation
