#!/usr/bin/env python3
"""
Local test script for DNS server functionality.
Tests SOA, NS, and A record queries.
"""

import socket
import struct
import json
import time
import threading
from dns_server import SimpleDNSServer


def create_dns_query(domain: str, qtype: int = 1) -> bytes:
    """Create a DNS query packet."""
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
        if part:  # Skip empty parts
            question += struct.pack('B', len(part)) + part.encode('utf-8')
    question += b'\x00'  # Null terminator
    question += struct.pack('>HH', qtype, 0x0001)  # QTYPE, QCLASS=IN
    
    return header + question


def parse_dns_response(data: bytes) -> dict:
    """Parse DNS response and return information."""
    if len(data) < 12:
        return {"error": "Response too short"}
    
    # Parse header
    flags = struct.unpack('>H', data[2:4])[0]
    rcode = flags & 0x0F
    qr = (flags >> 15) & 0x01
    aa = (flags >> 10) & 0x01
    
    answer_count = struct.unpack('>H', data[6:8])[0]
    
    result = {
        "qr": qr,
        "aa": aa,
        "rcode": rcode,
        "answer_count": answer_count,
        "answers": []
    }
    
    # Parse question section
    offset = 12
    domain_parts = []
    while offset < len(data) and data[offset] != 0:
        length = data[offset]
        offset += 1
        domain_parts.append(data[offset:offset + length].decode('utf-8'))
        offset += length
    offset += 5  # Skip null, QTYPE, QCLASS
    
    result["question"] = '.'.join(domain_parts)
    
    # Parse answer section
    for i in range(answer_count):
        if offset >= len(data):
            break
            
        # Check for name pointer
        if (data[offset] & 0xC0) == 0xC0:
            offset += 2  # Skip pointer
        else:
            # Skip name
            while offset < len(data) and data[offset] != 0:
                offset += data[offset] + 1
            offset += 1
        
        if offset + 10 > len(data):
            break
            
        qtype = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        qclass = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        ttl = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        data_length = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
        
        answer_data = data[offset:offset+data_length]
        offset += data_length
        
        answer = {
            "type": qtype,
            "class": qclass,
            "ttl": ttl,
            "data": answer_data
        }
        
        # Parse A record
        if qtype == 1 and data_length == 4:
            answer["ip"] = socket.inet_ntoa(answer_data)
        
        result["answers"].append(answer)
    
    return result


def test_query(server_port: int, domain: str, qtype: int, expected_rcode: int = 0, description: str = ""):
    """Test a DNS query."""
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Query: {domain} (type {qtype})")
    print(f"{'='*60}")
    
    query = create_dns_query(domain, qtype)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    try:
        sock.sendto(query, ('127.0.0.1', server_port))
        response, _ = sock.recvfrom(512)
        
        result = parse_dns_response(response)
        
        print(f"Response RCODE: {result['rcode']} (expected: {expected_rcode})")
        print(f"Authoritative: {result['aa']}")
        print(f"Answer count: {result['answer_count']}")
        
        if result['answers']:
            print("Answers:")
            for i, answer in enumerate(result['answers']):
                print(f"  {i+1}. Type: {answer['type']}, TTL: {answer['ttl']}")
                if 'ip' in answer:
                    print(f"     IP: {answer['ip']}")
        
        if result['rcode'] == expected_rcode:
            print("✅ PASS")
            return True
        else:
            print(f"❌ FAIL - Expected RCODE {expected_rcode}, got {result['rcode']}")
            return False
            
    except socket.timeout:
        print("❌ FAIL - Timeout")
        return False
    except Exception as e:
        print(f"❌ FAIL - Error: {e}")
        return False
    finally:
        sock.close()


def main():
    """Run local DNS server tests."""
    print("Starting Local DNS Server Tests")
    print("="*60)
    
    # Create test config with random port
    import random
    test_port = random.randint(10000, 65535)
    test_config = {
        "domain": "securityprox.net",
        "port": test_port,  # Use random port to avoid conflicts
        "host": "127.0.0.1"
    }
    
    with open("test_config.json", "w") as f:
        json.dump(test_config, f)
    
    # Create and start server
    server = SimpleDNSServer("test_config.json")
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    time.sleep(1)
    
    print(f"DNS Server started on port {test_config['port']}")
    print(f"Testing domain: {test_config['domain']}")
    
    # Run tests
    tests_passed = 0
    tests_total = 0
    
    # Test 1: SOA query for root domain
    tests_total += 1
    if test_query(test_port, "securityprox.net", 6, 0, "SOA query for root domain"):
        tests_passed += 1
    
    # Test 2: NS query for root domain
    tests_total += 1
    if test_query(test_port, "securityprox.net", 2, 0, "NS query for root domain"):
        tests_passed += 1
    
    # Test 3: A record query for valid IP subdomain
    tests_total += 1
    if test_query(test_port, "83-93-23-23.securityprox.net", 1, 0, "A record query for valid IP subdomain"):
        tests_passed += 1
    
    # Test 4: A record query for invalid IP subdomain
    tests_total += 1
    if test_query(test_port, "999-999-999-999.securityprox.net", 1, 3, "A record query for invalid IP subdomain (should be NXDOMAIN)"):
        tests_passed += 1
    
    # Test 5: Query for wrong domain
    tests_total += 1
    if test_query(test_port, "example.com", 1, 3, "Query for wrong domain (should be NXDOMAIN)"):
        tests_passed += 1
    
    # Test 6: Root domain A record (should be NXDOMAIN)
    tests_total += 1
    if test_query(test_port, "securityprox.net", 1, 3, "A record query for root domain (should be NXDOMAIN)"):
        tests_passed += 1
    
    # Cleanup
    if server.socket:
        server.socket.close()
    server_thread.join(timeout=1)
    
    import os
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Test Results: {tests_passed}/{tests_total} passed")
    print(f"{'='*60}")
    
    if tests_passed == tests_total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit(main())

