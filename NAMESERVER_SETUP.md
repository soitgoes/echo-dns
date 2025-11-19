# Nameserver Setup for securityprox.net

## The Problem

AWS can't register nameservers from a different domain (`nsdynspark.911cellular.com`) because the `.net` registry doesn't have glue records for them.

## Solution: Use Nameservers in Your Own Domain

You need to create nameservers that are subdomains of `securityprox.net`:

### Step 1: Create A Records for Nameservers

In your DNS server configuration (or wherever you manage DNS for `securityprox.net`), create A records:

- `ns1.securityprox.net` → `3.140.49.43`
- `ns2.securityprox.net` → `3.149.78.49`

### Step 2: Update Your DNS Server Code

Your DNS server needs to return these nameservers in NS responses instead of the old ones.

### Step 3: Update Nameservers at Registry

Once the A records exist and resolve, update the nameservers at AWS/registrar to:
- `ns1.securityprox.net`
- `ns2.securityprox.net`

## Alternative: Keep Route 53 Hosted Zone (Minimal)

If you can't use nameservers in your own domain (chicken-and-egg problem), you can:

1. **Recreate the Route 53 hosted zone** for `securityprox.net`
2. **Only add NS records** pointing to your nameservers:
   - `ns1.securityprox.net` → `3.140.49.43` (A record)
   - `ns2.securityprox.net` → `3.149.78.49` (A record)
   - NS record: `securityprox.net` → `ns1.securityprox.net`, `ns2.securityprox.net`
3. **Let your DNS server handle all subdomain queries**

This way Route 53 only handles the root domain delegation, and your server handles everything else.

## Recommended Approach

**Option 1: Use securityprox.net nameservers (Best)**
1. Create A records for `ns1.securityprox.net` and `ns2.securityprox.net` in your DNS server
2. Update DNS server code to return these in NS responses
3. Update registry nameservers to `ns1.securityprox.net` and `ns2.securityprox.net`

**Option 2: Minimal Route 53 zone (Easier)**
1. Recreate Route 53 hosted zone
2. Add only NS records and nameserver A records
3. Your DNS server handles all subdomain queries

