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
            "host": "0.0.0.0"
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
    
    def parse_dns_query(self, data: bytes) -> Optional[str]:
        """Parse DNS query and extract the domain name."""
        try:
            # Skip DNS header (12 bytes)
            offset = 12
            
            # Parse the question section
            domain_parts = []
            while offset < len(data):
                length = data[offset]
                if length == 0:
                    break
                offset += 1
                domain_parts.append(data[offset:offset + length].decode('utf-8'))
                offset += length
            
            # Skip QTYPE and QCLASS (4 bytes)
            offset += 4
            
            return '.'.join(domain_parts)
        except (IndexError, UnicodeDecodeError):
            return None
    
    def create_dns_response(self, query_data: bytes, ip_address: str) -> bytes:
        """Create a DNS response with the given IP address."""
        # Copy the query header
        response = bytearray(query_data[:12])
        
        # Set response flags (QR=1, AA=1, RA=1)
        response[2] = 0x81  # Response, Authoritative
        response[3] = 0x80  # Recursion available
        
        # Set answer count to 1
        response[6:8] = struct.pack('>H', 1)
        
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
    
    def create_error_response(self, query_data: bytes) -> bytes:
        """Create a DNS error response (NXDOMAIN)."""
        response = bytearray(query_data[:12])
        
        # Set response flags with error (QR=1, AA=1, RA=1, RCODE=3 for NXDOMAIN)
        response[2] = 0x81  # Response, Authoritative
        response[3] = 0x83  # Recursion available, NXDOMAIN
        
        # Set answer count to 0
        response[6:8] = struct.pack('>H', 0)
        
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
        domain = self.parse_dns_query(data)
        if not domain:
            return self.create_error_response(data)
        
        # Check if the domain ends with our configured domain
        if not domain.endswith('.' + self.config['domain']):
            return self.create_error_response(data)
        
        # Extract the subdomain part
        subdomain = domain[:-len('.' + self.config['domain'])]
        
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
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind((self.config['host'], self.config['port']))
            
            print(f"DNS Server started on {self.config['host']}:{self.config['port']}")
            print(f"Domain: {self.config['domain']}")
            print("Waiting for queries...")
            
            while True:
                try:
                    data, client_addr = self.socket.recvfrom(512)
                    response = self.handle_query(data, client_addr)
                    self.socket.sendto(response, client_addr)
                except KeyboardInterrupt:
                    print("\nShutting down server...")
                    break
                except Exception as e:
                    print(f"Error handling query: {e}")
                    
        except Exception as e:
            print(f"Error starting server: {e}")
        finally:
            if self.socket:
                self.socket.close()


def main():
    """Main function to start the DNS server."""
    server = SimpleDNSServer()
    server.start()


if __name__ == "__main__":
    main()
