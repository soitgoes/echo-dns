# securityprox.net DNS Setup Guide

## The Problem

AWS/Registry can't register nameservers from a different domain (`nsdynspark.911cellular.com`) because the registry doesn't have glue records for them. You need to use nameservers in your own domain.

## Solution: Use Nameservers in securityprox.net

### Step 1: Update DNS Server Configuration

Update your `config.json` on both servers to include:

```json
{
  "domain": "securityprox.net",
  "port": 53,
  "host": "0.0.0.0",
  "nameservers": ["ns1.securityprox.net", "ns2.securityprox.net"],
  "nameserver_ips": ["3.140.49.43", "3.149.78.49"]
}
```

### Step 2: Deploy Updated Code

The DNS server now supports:
- Configurable nameservers (via `nameservers` config)
- Nameserver A record responses (via `nameserver_ips` config)
- Automatic handling of nameserver hostname queries

### Step 3: Test Nameserver Resolution

After deploying, test that nameservers resolve:

```bash
dig ns1.securityprox.net @3.140.49.43
# Should return: 3.140.49.43

dig ns2.securityprox.net @3.149.78.49
# Should return: 3.149.78.49
```

### Step 4: Update Nameservers at Registry

Once nameservers resolve correctly, update at AWS/registrar:

1. Go to Route 53 → Registered Domains → `securityprox.net`
2. Click "Add or edit nameservers"
3. Add:
   - `ns1.securityprox.net`
   - `ns2.securityprox.net`
4. Save

### Step 5: Wait for Propagation

- Registry updates: 15 minutes to 48 hours
- DNS propagation: Usually within a few hours

### Step 6: Verify

```bash
# Check whois (should show your nameservers, not AWS)
whois securityprox.net | grep -i "name server"

# Test with Google DNS
dig 85-93-23-23.securityprox.net @8.8.8.8
# Should now work!
```

## How It Works

1. **Nameserver A Records**: When someone queries `ns1.securityprox.net`, your DNS server returns the IP from `nameserver_ips[0]`
2. **NS Records**: When someone queries NS for `securityprox.net`, your server returns `ns1.securityprox.net` and `ns2.securityprox.net`
3. **Registry**: The registry can resolve your nameservers because they're in your own domain

## Troubleshooting

If registry still can't find nameservers:
1. Verify nameservers resolve: `dig ns1.securityprox.net @8.8.8.8`
2. Wait longer for propagation (can take up to 48 hours)
3. Check that both nameservers are responding correctly

