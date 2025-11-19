# DNS Troubleshooting Guide

## Current Situation

- ✅ NS records exist in AWS Route 53 (`911cellular.com` hosted zone)
- ✅ AWS nameservers return the NS records correctly
- ✅ Your DNS server responds correctly with authoritative answers
- ❌ Google DNS (8.8.8.8) still returns NXDOMAIN (likely cached)

## Why IPv6 Support Won't Fix NS Record Visibility

Adding IPv6 support to your DNS server (listening on IPv6) is good, but it **doesn't affect** whether NS records are visible. The NS record visibility depends on:

1. **DNS delegation in the parent zone** - ✅ You have this
2. **Nameserver hostname resolution** - ✅ `nsdynspark.911cellular.com` resolves to `3.140.49.43`
3. **DNS propagation** - ⚠️ This is the issue

## What You Should Do

### 1. Add AAAA Record for Nameserver Hostname (Optional but Recommended)

While not required, adding an IPv6 AAAA record for your nameserver hostname can help:

**In Route 53 (`911cellular.com` hosted zone):**
- **Record name**: `nsdynspark` (or `nsdynspark.911cellular.com`)
- **Type**: `AAAA`
- **Value**: Your DNS server's IPv6 address (if it has one)
- **TTL**: `300` or `3600`

**Note**: Only add this if your DNS server has a public IPv6 address. If you just added IPv6 listening support but don't have a public IPv6 address, skip this.

### 2. Verify Record Name Format in Route 53

In Route 53, when you're in the `911cellular.com` hosted zone:
- ✅ **Correct**: Record name = `dynspark` (just the subdomain)
- ❌ **Wrong**: Record name = `dynspark.911cellular.com` (FQDN)

Route 53 automatically appends the zone name, so using the FQDN would create `dynspark.911cellular.com.911cellular.com`.

### 3. Add Both Nameservers to the Same NS Record

Make sure your NS record includes **both** nameservers:
- `nsdynspark.911cellular.com.`
- `nsdynspark2.911cellular.com.`

### 4. Clear DNS Cache (For Testing)

Google DNS and other public resolvers cache NXDOMAIN responses aggressively. To test if it's working:

```bash
# Query AWS nameservers directly (should work)
dig NS dynspark.911cellular.com @ns-628.awsdns-14.net

# Query your DNS server directly (should work)
dig 192-168-1-69.dynspark.911cellular.com @3.140.49.43

# Try different public DNS servers
dig NS dynspark.911cellular.com @1.1.1.1
dig NS dynspark.911cellular.com @208.67.222.222  # OpenDNS
```

### 5. Wait for Cache Expiration

NXDOMAIN responses can be cached for:
- **Negative TTL** (from SOA record): Usually 300-3600 seconds
- **Some resolvers**: Up to 24-48 hours

Since it's been a month, there might be another issue. Check:

1. **Record name format** - Make sure it's just `dynspark`, not `dynspark.911cellular.com`
2. **Record type** - Must be `NS`
3. **Record values** - Must be valid hostnames ending with `.`

## Verification Commands

```bash
# Check NS record from AWS (should work)
dig NS dynspark.911cellular.com @ns-628.awsdns-14.net

# Check nameserver A record
dig A nsdynspark.911cellular.com @8.8.8.8

# Check nameserver AAAA record (if you add one)
dig AAAA nsdynspark.911cellular.com @8.8.8.8

# Test actual query
dig 192-168-1-69.dynspark.911cellular.com @3.140.49.43
```

## Most Likely Issue

Given that:
- Records have been published for a month
- AWS nameservers have the records
- Google DNS still returns NXDOMAIN

The most likely cause is **cached NXDOMAIN responses** combined with potentially:
1. Record name format issue in Route 53
2. Missing second nameserver in the NS record
3. Negative caching by public DNS servers

Try querying different DNS servers to see if any have picked it up yet.


