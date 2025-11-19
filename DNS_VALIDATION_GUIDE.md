# DNS Response Validation Guide

## Using dig to Validate Responses

### Basic Validation
```bash
# Test with verbose output
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net +noall +comments +stats

# Check for malformed packet warnings
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net
# Look for: "Warning: Message parser reports malformed message packet"
```

### Detailed Packet Analysis
```bash
# Show raw packet data
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net +bufsize=4096

# Show all sections
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net +noall +answer +authority +additional

# Test different query types
dig @127.0.0.1 -p 5353 securityprox.net SOA
dig @127.0.0.1 -p 5353 securityprox.net NS
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net A
```

## Using Python Validation Script

```bash
# Make script executable
chmod +x validate_dns_response.py

# Run validation tests
python3 validate_dns_response.py
```

The script will:
- Validate header format (all 12 bytes)
- Check QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT
- Validate question section format
- Validate answer section format
- Check for proper null terminators
- Verify label lengths (max 63 bytes)
- Check RDATA lengths match RDLENGTH

## Using drill (ldns)

```bash
# Install drill (if not available)
# macOS: brew install ldns
# Ubuntu: sudo apt-get install ldnsutils

# Test query
drill @127.0.0.1 -p 5353 85-93-23-23.securityprox.net

# Verbose mode
drill @127.0.0.1 -p 5353 85-93-23-23.securityprox.net -V
```

## Using Wireshark/tcpdump

Capture and analyze DNS packets:

```bash
# Capture DNS traffic
sudo tcpdump -i any -n -s 0 -X port 53

# In another terminal, run a query
dig @127.0.0.1 -p 5353 85-93-23-23.securityprox.net

# Or use Wireshark GUI for visual analysis
sudo wireshark
# Filter: dns and port 53
```

## RFC 1035 Compliance Checklist

### Header (12 bytes)
- [ ] ID field (2 bytes) - preserved from query
- [ ] Flags (2 bytes) - QR=1, AA=1, RA=1, RCODE=0
- [ ] QDCOUNT (2 bytes) - should be 1
- [ ] ANCOUNT (2 bytes) - number of answers
- [ ] NSCOUNT (2 bytes) - should be 0 for simple responses
- [ ] ARCOUNT (2 bytes) - should be 0 (or 1 if EDNS OPT present)

### Question Section
- [ ] Domain name in label format
- [ ] Each label ≤ 63 bytes
- [ ] Null terminator (0x00)
- [ ] QTYPE (2 bytes)
- [ ] QCLASS (2 bytes)

### Answer Section
- [ ] NAME (compressed pointer 0xC00C or label sequence)
- [ ] TYPE (2 bytes)
- [ ] CLASS (2 bytes)
- [ ] TTL (4 bytes)
- [ ] RDLENGTH (2 bytes)
- [ ] RDATA (length = RDLENGTH)

## Common Issues to Check

1. **Malformed packet warning**: Usually means header counts don't match actual sections
2. **Wrong answer count**: ANCOUNT doesn't match number of answer records
3. **Missing null terminators**: Question section or name labels not properly terminated
4. **Invalid label lengths**: Labels > 63 bytes
5. **RDATA length mismatch**: RDLENGTH doesn't match actual RDATA size
6. **NSCOUNT/ARCOUNT not zero**: Should be 0 for simple A/SOA/NS responses

## Testing Against Production

```bash
# Test against production servers
dig @3.140.49.43 85-93-23-23.securityprox.net +noall +comments
dig @3.149.78.49 85-93-23-23.securityprox.net +noall +comments

# Check for warnings
dig @3.140.49.43 85-93-23-23.securityprox.net 2>&1 | grep -i warning
```

## Online DNS Validators

- **DNS Checker**: https://dnschecker.org/
- **MXToolbox**: https://mxtoolbox.com/DNSLookup.aspx
- **DNS Propagation Checker**: https://www.whatsmydns.net/

These can help verify responses from different locations worldwide.

