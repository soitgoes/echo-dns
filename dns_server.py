#!/usr/bin/env python3
"""
Simple DNS Server that converts subdomain dashes to dots for IP addresses.
Example: 192-168-1-1.somedomain.com -> 192.168.1.1
"""

import socket
import struct
import json
import os
import ipaddress
import select
from typing import Optional, Tuple


class SimpleDNSServer:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.socket = None
        
    def load_config(self) -> dict:
        """Load configuration from JSON file."""
        default_config = {
            "domain": "somedomain.com",
            "port": 53,
            "host": "0.0.0.0",
            "nameservers": ["ns1.somedomain.com", "ns2.somedomain.com"],
            "nameserver_ips": ["127.0.0.1", "127.0.0.1"]  # IP addresses for nameservers
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults for missing keys
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config file: {e}")
                print("Using default configuration")
        
        # Create default config file
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        print(f"Created default config file: {self.config_file}")
        
        return default_config
    
    def is_valid_ip(self, ip_str: str) -> bool:
        """Check if the string is a valid IP address."""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    def parse_dns_query(self, data: bytes) -> Optional[Tuple[str, int]]:
        """Parse DNS query and extract the domain name and query type.
        Returns (domain, qtype) or None if parsing fails."""
        try:
            # Skip DNS header (12 bytes)
            offset = 12
            
            # Parse the question section
            domain_parts = []
            while offset < len(data):
                length = data[offset]
                if length == 0:
                    offset += 1  # Skip the null terminator
                    break
                offset += 1
                domain_parts.append(data[offset:offset + length].decode('utf-8'))
                offset += length
            
            # Get QTYPE (2 bytes) - offset now points after the null terminator
            if offset + 2 > len(data):
                return None
            qtype = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 4  # Skip QTYPE and QCLASS
            
            domain = '.'.join(domain_parts)
            return (domain, qtype)
        except (IndexError, UnicodeDecodeError):
            return None
    
    def create_dns_response(self, query_data: bytes, ip_address: str) -> bytes:
        """Create a DNS response with the given IP address."""
        # Copy the query header
        response = bytearray(query_data[:12])
        
        # Set response flags (QR=1, AA=1, RA=1)
        # Byte 2: QR(1) + Opcode(0000) + AA(1) + TC(0) + RD(preserve from query)
        # Byte 3: RA(1) + Z(000) + RCODE(0000)
        response[2] = 0x84 | (query_data[2] & 0x01)  # Response, Authoritative, preserve RD
        response[3] = 0x80  # Recursion available
        
        # Header fields (RFC 1035):
        # Bytes 4-5: QDCOUNT (question count) - preserve from query (should be 1)
        # Bytes 6-7: ANCOUNT (answer count) - set to 1
        # Bytes 8-9: NSCOUNT (authority count) - set to 0
        # Bytes 10-11: ARCOUNT (additional count) - set to 0
        response[6:8] = struct.pack('>H', 1)  # ANCOUNT = 1
        response[8:10] = struct.pack('>H', 0)  # NSCOUNT = 0
        response[10:12] = struct.pack('>H', 0)  # ARCOUNT = 0
        
        # Copy the question section
        question_start = 12
        question_end = question_start
        while question_end < len(query_data) and query_data[question_end] != 0:
            question_end += query_data[question_end] + 1
        question_end += 5  # Include null terminator and QTYPE/QCLASS
        
        response.extend(query_data[question_start:question_end])
        
        # Add answer section
        # Name pointer to question (0xC00C)
        response.extend(b'\xc0\x0c')
        
        # Type A (0x0001)
        response.extend(b'\x00\x01')
        
        # Class IN (0x0001)
        response.extend(b'\x00\x01')
        
        # TTL (300 seconds)
        response.extend(b'\x00\x00\x01\x2c')
        
        # Data length (4 bytes for IPv4)
        response.extend(b'\x00\x04')
        
        # IP address
        ip_bytes = socket.inet_aton(ip_address)
        response.extend(ip_bytes)
        
        return bytes(response)
    
    def create_soa_response(self, query_data: bytes) -> bytes:
        """Create a DNS SOA response."""
        response = bytearray(query_data[:12])
        
        # Set response flags (QR=1, AA=1, RA=1)
        response[2] = 0x84 | (query_data[2] & 0x01)  # Response, Authoritative, preserve RD
        response[3] = 0x80  # Recursion available
        
        # Set header counts (RFC 1035)
        response[6:8] = struct.pack('>H', 1)  # ANCOUNT = 1
        response[8:10] = struct.pack('>H', 0)  # NSCOUNT = 0
        response[10:12] = struct.pack('>H', 0)  # ARCOUNT = 0
        
        # Copy the question section
        question_start = 12
        question_end = question_start
        while question_end < len(query_data) and query_data[question_end] != 0:
            question_end += query_data[question_end] + 1
        question_end += 5  # Include null terminator and QTYPE/QCLASS
        
        response.extend(query_data[question_start:question_end])
        
        # Add SOA answer section
        # Name pointer to question (0xC00C)
        response.extend(b'\xc0\x0c')
        
        # Type SOA (0x0006)
        response.extend(b'\x00\x06')
        
        # Class IN (0x0001)
        response.extend(b'\x00\x01')
        
        # TTL (3600 seconds)
        response.extend(b'\x00\x00\x0e\x10')
        
        # Data length (will calculate)
        soa_start = len(response)
        response.extend(b'\x00\x00')  # Placeholder for length
        
        # MNAME (primary nameserver) - use first nameserver from config
        nameservers = self.config.get('nameservers', [f"ns1.{self.config['domain']}", f"ns2.{self.config['domain']}"])
        mname = nameservers[0] if nameservers else f"ns1.{self.config['domain']}"
        for part in mname.split('.'):
            response.append(len(part))
            response.extend(part.encode('utf-8'))
        response.append(0)  # Null terminator
        
        # RNAME (responsible person email - format: hostmaster.domain)
        rname = f"hostmaster.{self.config['domain']}"
        for part in rname.split('.'):
            response.append(len(part))
            response.extend(part.encode('utf-8'))
        response.append(0)  # Null terminator
        
        # Serial number (1)
        response.extend(struct.pack('>I', 1))
        
        # Refresh (7200 seconds = 2 hours)
        response.extend(struct.pack('>I', 7200))
        
        # Retry (900 seconds = 15 minutes)
        response.extend(struct.pack('>I', 900))
        
        # Expire (1209600 seconds = 2 weeks)
        response.extend(struct.pack('>I', 1209600))
        
        # Minimum TTL (86400 seconds = 1 day)
        response.extend(struct.pack('>I', 86400))
        
        # Update data length
        soa_length = len(response) - soa_start - 2
        response[soa_start:soa_start+2] = struct.pack('>H', soa_length)
        
        return bytes(response)
    
    def create_ns_response(self, query_data: bytes) -> bytes:
        """Create a DNS NS response."""
        response = bytearray(query_data[:12])
        
        # Set response flags (QR=1, AA=1, RA=1)
        response[2] = 0x84 | (query_data[2] & 0x01)  # Response, Authoritative, preserve RD
        response[3] = 0x80  # Recursion available
        
        # Get nameservers count
        nameservers = self.config.get('nameservers', [f"ns1.{self.config['domain']}", f"ns2.{self.config['domain']}"])
        ns_count = min(len(nameservers), 2)  # Limit to 2 nameservers
        
        # Set header counts (RFC 1035)
        response[6:8] = struct.pack('>H', ns_count)  # ANCOUNT = number of nameservers
        response[8:10] = struct.pack('>H', 0)  # NSCOUNT = 0
        response[10:12] = struct.pack('>H', 0)  # ARCOUNT = 0
        
        # Copy the question section
        question_start = 12
        question_end = question_start
        while question_end < len(query_data) and query_data[question_end] != 0:
            question_end += query_data[question_end] + 1
        question_end += 5  # Include null terminator and QTYPE/QCLASS
        
        response.extend(query_data[question_start:question_end])
        
        # Get nameservers from config
        nameservers = self.config.get('nameservers', [f"ns1.{self.config['domain']}", f"ns2.{self.config['domain']}"])
        if len(nameservers) < 2:
            # Ensure we have at least 2 nameservers
            nameservers = nameservers + [f"ns2.{self.config['domain']}"]
        
        # Add NS records for each nameserver
        for ns_name in nameservers[:2]:  # Limit to 2 nameservers
            response.extend(b'\xc0\x0c')  # Name pointer
            response.extend(b'\x00\x02')  # Type NS
            response.extend(b'\x00\x01')  # Class IN
            response.extend(b'\x00\x00\x0e\x10')  # TTL 3600
            
            ns_start = len(response)
            response.extend(b'\x00\x00')  # Placeholder for length
            for part in ns_name.split('.'):
                response.append(len(part))
                response.extend(part.encode('utf-8'))
            response.append(0)
            ns_length = len(response) - ns_start - 2
            response[ns_start:ns_start+2] = struct.pack('>H', ns_length)
        
        return bytes(response)
    
    def create_error_response(self, query_data: bytes) -> bytes:
        """Create a DNS error response (NXDOMAIN)."""
        response = bytearray(query_data[:12])
        
        # Set response flags with error (QR=1, AA=1, RA=1, RCODE=3 for NXDOMAIN)
        # Byte 2: QR(1) + Opcode(0000) + AA(1) + TC(0) + RD(preserve from query)
        # Byte 3: RA(1) + Z(000) + RCODE(0011 for NXDOMAIN)
        response[2] = 0x84 | (query_data[2] & 0x01)  # Response, Authoritative, preserve RD
        response[3] = 0x83  # Recursion available, NXDOMAIN
        
        # Set header counts (RFC 1035)
        response[6:8] = struct.pack('>H', 0)  # ANCOUNT = 0
        response[8:10] = struct.pack('>H', 0)  # NSCOUNT = 0
        response[10:12] = struct.pack('>H', 0)  # ARCOUNT = 0
        
        # Copy the question section
        question_start = 12
        question_end = question_start
        while question_end < len(query_data) and query_data[question_end] != 0:
            question_end += query_data[question_end] + 1
        question_end += 5  # Include null terminator and QTYPE/QCLASS
        
        response.extend(query_data[question_start:question_end])
        
        return bytes(response)
    
    def handle_query(self, data: bytes, client_addr: Tuple[str, int]) -> bytes:
        """Handle a DNS query and return the appropriate response."""
        parsed = self.parse_dns_query(data)
        if not parsed:
            print(f"Failed to parse query from {client_addr}")
            return self.create_error_response(data)
        
        domain, qtype = parsed
        
        # Normalize domain (remove trailing dot if present, convert to lowercase for comparison)
        domain_normalized = domain.rstrip('.').lower()
        config_domain_normalized = self.config['domain'].rstrip('.').lower()
        
        # Debug output
        print(f"Query: domain={domain}, normalized={domain_normalized}, config={config_domain_normalized}, qtype={qtype}")
        
        # Check if the domain matches our configured domain or is a subdomain
        is_root_domain = domain_normalized == config_domain_normalized
        is_subdomain = domain_normalized.endswith('.' + config_domain_normalized)
        
        if not is_root_domain and not is_subdomain:
            print(f"Domain mismatch: {domain_normalized} does not match {config_domain_normalized}")
            return self.create_error_response(data)
        
        # Handle queries for the root domain
        if is_root_domain:
            if qtype == 6:  # SOA
                print(f"SOA query for {domain}")
                return self.create_soa_response(data)
            elif qtype == 2:  # NS
                print(f"NS query for {domain}")
                return self.create_ns_response(data)
            else:
                # For other query types on root domain, return NXDOMAIN
                return self.create_error_response(data)
        
        # Handle subdomain queries (A records only)
        if qtype != 1:  # Not an A record query
            return self.create_error_response(data)
        
        # Extract the subdomain part
        subdomain = domain_normalized[:-len('.' + config_domain_normalized)]
        
        # Handle nameserver hostnames (ns1.domain.com, ns2.domain.com, etc.)
        nameservers = self.config.get('nameservers', [f"ns1.{self.config['domain']}", f"ns2.{self.config['domain']}"])
        nameserver_ips = self.config.get('nameserver_ips', [])
        
        # Check if this is a nameserver hostname
        for i, ns_name in enumerate(nameservers):
            ns_normalized = ns_name.rstrip('.').lower()
            if domain_normalized == ns_normalized:
                # Return the corresponding IP address
                if i < len(nameserver_ips) and self.is_valid_ip(nameserver_ips[i]):
                    print(f"Nameserver query for {domain} -> {nameserver_ips[i]}")
                    return self.create_dns_response(data, nameserver_ips[i])
                else:
                    # Fallback: try to extract from nameserver hostname pattern
                    # If nameserver is ns1.domain.com and server IP is known, use it
                    print(f"Nameserver query for {domain} but no IP configured")
                    return self.create_error_response(data)
        
        # Convert dashes to dots
        potential_ip = subdomain.replace('-', '.')
        
        # Validate if it's a valid IP address
        if self.is_valid_ip(potential_ip):
            print(f"Query for {domain} -> {potential_ip}")
            return self.create_dns_response(data, potential_ip)
        else:
            print(f"Invalid IP in query: {domain} -> {potential_ip}")
            return self.create_error_response(data)
    
    def start(self):
        """Start the DNS server."""
        sockets = []
        try:
            # Create IPv4 socket
            ipv4_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ipv4_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind IPv4 socket
            bind_host = self.config['host']
            if bind_host == '0.0.0.0':
                # For 0.0.0.0, also try to bind IPv6
                try:
                    ipv6_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
                    ipv6_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    # Disable IPv4-mapped IPv6 addresses to force separate IPv4/IPv6 sockets
                    ipv6_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                    ipv6_socket.bind(('::', self.config['port']))
                    sockets.append(ipv6_socket)
                    print(f"DNS Server IPv6 socket bound on [::]:{self.config['port']}")
                except (OSError, AttributeError) as e:
                    # IPv6 not available or not supported, continue with IPv4 only
                    print(f"IPv6 not available, using IPv4 only: {e}")
            
            ipv4_socket.bind((bind_host, self.config['port']))
            sockets.append(ipv4_socket)
            self.socket = ipv4_socket  # Keep reference for cleanup
            
            print(f"DNS Server started on {bind_host}:{self.config['port']}")
            print(f"Domain: {self.config['domain']}")
            print("Waiting for queries...")
            
            while True:
                try:
                    # Use select to handle multiple sockets
                    if len(sockets) > 1:
                        readable, _, _ = select.select(sockets, [], [])
                        for sock in readable:
                            data, client_addr = sock.recvfrom(512)
                            print(f"Received query from {client_addr}, length={len(data)}")
                            response = self.handle_query(data, client_addr)
                            sock.sendto(response, client_addr)
                    else:
                        data, client_addr = ipv4_socket.recvfrom(512)
                        print(f"Received query from {client_addr}, length={len(data)}")
                        response = self.handle_query(data, client_addr)
                        ipv4_socket.sendto(response, client_addr)
                except KeyboardInterrupt:
                    print("\nShutting down server...")
                    break
                except Exception as e:
                    print(f"Error handling query: {e}")
                    
        except Exception as e:
            print(f"Error starting server: {e}")
        finally:
            for sock in sockets:
                if sock:
                    sock.close()


def main():
    """Main function to start the DNS server."""
    server = SimpleDNSServer()
    server.start()


if __name__ == "__main__":
    main()
