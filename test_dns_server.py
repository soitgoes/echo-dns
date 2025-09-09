#!/usr/bin/env python3
"""
Test script for the DNS server.
"""

import socket
import struct
import threading
import time
import unittest
from dns_server import SimpleDNSServer


class TestDNSServer(unittest.TestCase):
    def setUp(self):
        """Set up test configuration."""
        import random
        self.test_config = {
            "domain": "testdomain.com",
            "port": random.randint(10000, 65535),  # Use random port to avoid conflicts
            "host": "127.0.0.1"
        }
        
        # Write test config
        import json
        with open("test_config.json", "w") as f:
            json.dump(self.test_config, f)
        
        self.server = SimpleDNSServer("test_config.json")
        self.server_thread = None
        
    def tearDown(self):
        """Clean up after tests."""
        if self.server_thread and self.server_thread.is_alive():
            # Server will stop when socket is closed
            if self.server.socket:
                self.server.socket.close()
            self.server_thread.join(timeout=1)
        
        # Clean up test config
        import os
        if os.path.exists("test_config.json"):
            os.remove("test_config.json")
    
    def start_server(self):
        """Start the server in a separate thread."""
        self.server_thread = threading.Thread(target=self.server.start)
        self.server_thread.daemon = True
        self.server_thread.start()
        time.sleep(0.5)  # Give server more time to start
    
    def create_dns_query(self, domain: str) -> bytes:
        """Create a simple DNS query packet."""
        # DNS header
        header = struct.pack('>HHHHHH', 
                           0x1234,  # Transaction ID
                           0x0100,  # Flags (standard query)
                           0x0001,  # Questions
                           0x0000,  # Answer RRs
                           0x0000,  # Authority RRs
                           0x0000)  # Additional RRs
        
        # Question section
        question = b''
        for part in domain.split('.'):
            question += struct.pack('B', len(part)) + part.encode('utf-8')
        question += b'\x00'  # Null terminator
        question += struct.pack('>HH', 0x0001, 0x0001)  # QTYPE=A, QCLASS=IN
        
        return header + question
    
    def parse_dns_response(self, data: bytes) -> tuple:
        """Parse DNS response and return (ip_address, rcode)."""
        if len(data) < 12:
            return None, None
            
        # Parse header
        flags = struct.unpack('>H', data[2:4])[0]
        rcode = flags & 0x0F
        
        if rcode != 0:  # Error response
            return None, rcode
            
        # Parse answer section
        # Skip question section
        offset = 12
        while offset < len(data) and data[offset] != 0:
            offset += data[offset] + 1
        offset += 5  # Skip null terminator and QTYPE/QCLASS
        
        if offset + 12 > len(data):  # No answer section
            return None, rcode
            
        # Skip name pointer, type, class, TTL
        offset += 12
        
        # Get data length
        data_length = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        
        if data_length == 4:  # IPv4 address
            ip_bytes = data[offset:offset+4]
            ip_address = socket.inet_ntoa(ip_bytes)
            return ip_address, rcode
            
        return None, rcode
    
    def test_valid_ip_conversion(self):
        """Test conversion of valid IP addresses."""
        self.start_server()
        
        test_cases = [
            ("192-168-1-1.testdomain.com", "192.168.1.1"),
            ("10-0-0-1.testdomain.com", "10.0.0.1"),
            ("8-8-8-8.testdomain.com", "8.8.8.8"),
            ("127-0-0-1.testdomain.com", "127.0.0.1")
        ]
        
        for domain, expected_ip in test_cases:
            with self.subTest(domain=domain):
                query = self.create_dns_query(domain)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.0)
                try:
                    sock.sendto(query, (self.test_config['host'], self.test_config['port']))
                    response, _ = sock.recvfrom(512)
                    
                    ip_address, rcode = self.parse_dns_response(response)
                    self.assertEqual(rcode, 0, f"Expected success response for {domain}")
                    self.assertEqual(ip_address, expected_ip, f"Expected {expected_ip} for {domain}")
                finally:
                    sock.close()
    
    def test_invalid_ip_handling(self):
        """Test handling of invalid IP addresses."""
        self.start_server()
        
        invalid_cases = [
            "999-999-999-999.testdomain.com",
            "256-1-1-1.testdomain.com",
            "not-an-ip.testdomain.com",
            "192-168-1.testdomain.com"  # Only 3 octets
        ]
        
        for domain in invalid_cases:
            with self.subTest(domain=domain):
                query = self.create_dns_query(domain)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.0)
                try:
                    sock.sendto(query, (self.test_config['host'], self.test_config['port']))
                    response, _ = sock.recvfrom(512)
                    
                    ip_address, rcode = self.parse_dns_response(response)
                    self.assertEqual(rcode, 3, f"Expected NXDOMAIN for {domain}")  # NXDOMAIN = 3
                    self.assertIsNone(ip_address, f"Expected no IP for {domain}")
                finally:
                    sock.close()
    
    def test_wrong_domain(self):
        """Test queries for wrong domain."""
        self.start_server()
        
        query = self.create_dns_query("192-168-1-1.wrongdomain.com")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        try:
            sock.sendto(query, (self.test_config['host'], self.test_config['port']))
            response, _ = sock.recvfrom(512)
            
            ip_address, rcode = self.parse_dns_response(response)
            self.assertEqual(rcode, 3, "Expected NXDOMAIN for wrong domain")
            self.assertIsNone(ip_address, "Expected no IP for wrong domain")
        finally:
            sock.close()
    
    def test_ip_validation(self):
        """Test IP address validation function."""
        # Valid IPs
        valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "8.8.8.8"]
        for ip in valid_ips:
            self.assertTrue(self.server.is_valid_ip(ip), f"{ip} should be valid")
        
        # Invalid IPs
        invalid_ips = ["999.999.999.999", "256.1.1.1", "192.168.1", "not-an-ip"]
        for ip in invalid_ips:
            self.assertFalse(self.server.is_valid_ip(ip), f"{ip} should be invalid")


if __name__ == "__main__":
    unittest.main()
