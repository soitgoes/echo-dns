#!/usr/bin/env python3
"""
Validate DNS response format against RFC 1035 specification.
"""

import socket
import struct
import sys


def validate_dns_response(data: bytes):
    """Validate DNS response against RFC 1035.
    Returns (is_valid, list_of_errors)."""
    errors = []
    
    if len(data) < 12:
        return False, ["Response too short: less than 12 bytes (header)"]
    
    # Parse header
    id_field = struct.unpack('>H', data[0:2])[0]
    flags = struct.unpack('>H', data[2:4])[0]
    qdcount = struct.unpack('>H', data[4:6])[0]
    ancount = struct.unpack('>H', data[6:8])[0]
    nscount = struct.unpack('>H', data[8:10])[0]
    arcount = struct.unpack('>H', data[10:12])[0]
    
    # Validate header fields
    qr = (flags >> 15) & 0x01
    opcode = (flags >> 11) & 0x0F
    aa = (flags >> 10) & 0x01
    tc = (flags >> 9) & 0x01
    rd = (flags >> 8) & 0x01
    ra = (flags >> 7) & 0x01
    rcode = flags & 0x0F
    
    # Check QR bit (must be 1 for response)
    if qr != 1:
        errors.append("QR bit must be 1 for responses")
    
    # Check QDCOUNT (should be 1 for standard queries)
    if qdcount != 1:
        errors.append(f"QDCOUNT should be 1, got {qdcount}")
    
    # Validate question section
    offset = 12
    question_valid = True
    try:
        # Parse domain name
        domain_parts = []
        while offset < len(data) and data[offset] != 0:
            length = data[offset]
            if length > 63:
                errors.append(f"Invalid label length: {length} (max 63)")
                question_valid = False
                break
            offset += 1
            if offset + length > len(data):
                errors.append("Question section extends beyond packet")
                question_valid = False
                break
            domain_parts.append(data[offset:offset + length].decode('utf-8', errors='ignore'))
            offset += length
        
        if question_valid and offset < len(data):
            if data[offset] != 0:
                errors.append("Question section missing null terminator")
            else:
                offset += 1  # Skip null terminator
                if offset + 4 > len(data):
                    errors.append("Question section incomplete (missing QTYPE/QCLASS)")
                else:
                    qtype = struct.unpack('>H', data[offset:offset+2])[0]
                    qclass = struct.unpack('>H', data[offset+2:offset+4])[0]
                    offset += 4
    except Exception as e:
        errors.append(f"Error parsing question section: {e}")
        question_valid = False
    
    # Validate answer section
    if ancount > 0:
        for i in range(ancount):
            if offset >= len(data):
                errors.append(f"Answer section incomplete (answer {i+1})")
                break
            
            # Parse name (could be pointer or label sequence)
            name_start = offset
            if (data[offset] & 0xC0) == 0xC0:
                # Name pointer
                if offset + 2 > len(data):
                    errors.append(f"Answer {i+1}: Name pointer incomplete")
                    break
                offset += 2
            else:
                # Label sequence
                while offset < len(data) and data[offset] != 0:
                    length = data[offset]
                    if length > 63:
                        errors.append(f"Answer {i+1}: Invalid label length: {length}")
                        break
                    offset += 1
                    if offset + length > len(data):
                        errors.append(f"Answer {i+1}: Label extends beyond packet")
                        break
                    offset += length
                if offset < len(data):
                    offset += 1  # Skip null terminator
            
            # Parse TYPE, CLASS, TTL, RDLENGTH
            if offset + 10 > len(data):
                errors.append(f"Answer {i+1}: Incomplete (missing TYPE/CLASS/TTL/RDLENGTH)")
                break
            
            rtype = struct.unpack('>H', data[offset:offset+2])[0]
            rclass = struct.unpack('>H', data[offset+2:offset+4])[0]
            ttl = struct.unpack('>I', data[offset+4:offset+8])[0]
            rdlength = struct.unpack('>H', data[offset+8:offset+10])[0]
            offset += 10
            
            # Validate RDATA length
            if offset + rdlength > len(data):
                errors.append(f"Answer {i+1}: RDATA extends beyond packet (length={rdlength})")
                break
            
            # Validate A record
            if rtype == 1 and rclass == 1:  # A record, IN class
                if rdlength != 4:
                    errors.append(f"Answer {i+1}: A record RDATA length should be 4, got {rdlength}")
            
            offset += rdlength
    
    # Check if we've consumed the expected amount
    expected_min = 12 + (offset - 12)  # Header + what we've parsed
    if len(data) < expected_min:
        errors.append(f"Packet shorter than expected: {len(data)} < {expected_min}")
    
    # Check NSCOUNT and ARCOUNT (should be 0 for simple responses)
    if nscount != 0:
        errors.append(f"NSCOUNT should be 0 for simple responses, got {nscount}")
    if arcount != 0:
        # ARCOUNT might be non-zero if OPT record is present (EDNS), that's OK
        if arcount > 1:
            errors.append(f"ARCOUNT unexpectedly high: {arcount}")
    
    return len(errors) == 0, errors


def test_query(server_host: str, server_port: int, domain: str, qtype: int = 1):
    """Test a DNS query and validate the response."""
    print(f"\n{'='*60}")
    print(f"Testing: {domain} (type {qtype}) @ {server_host}:{server_port}")
    print(f"{'='*60}")
    
    # Create DNS query
    query_id = 0x1234
    header = struct.pack('>HHHHHH',
                         query_id,      # ID
                         0x0100,        # Flags (standard query)
                         0x0001,        # QDCOUNT
                         0x0000,        # ANCOUNT
                         0x0000,        # NSCOUNT
                         0x0000)        # ARCOUNT
    
    question = b''
    for part in domain.split('.'):
        if part:
            question += struct.pack('B', len(part)) + part.encode('utf-8')
    question += b'\x00'  # Null terminator
    question += struct.pack('>HH', qtype, 0x0001)  # QTYPE, QCLASS
    
    query = header + question
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    try:
        sock.sendto(query, (server_host, server_port))
        response, _ = sock.recvfrom(512)
        
        print(f"Response received: {len(response)} bytes")
        
        is_valid, errors = validate_dns_response(response)
        
        if is_valid:
            print("✅ Response is RFC 1035 compliant")
            return True
        else:
            print("❌ Response has RFC 1035 compliance issues:")
            for error in errors:
                print(f"   - {error}")
            return False
            
    except socket.timeout:
        print("❌ Timeout waiting for response")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        sock.close()


def main():
    """Run validation tests."""
    print("DNS Response RFC 1035 Compliance Validator")
    print("="*60)
    
    # Test against local server
    import json
    import os
    
    config_file = "test_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        port = config.get('port', 5353)
    else:
        port = 5353
    
    tests_passed = 0
    tests_total = 0
    
    # Test A record
    tests_total += 1
    if test_query('127.0.0.1', port, '85-93-23-23.securityprox.net', 1):
        tests_passed += 1
    
    # Test SOA record
    tests_total += 1
    if test_query('127.0.0.1', port, 'securityprox.net', 6):
        tests_passed += 1
    
    # Test NS record
    tests_total += 1
    if test_query('127.0.0.1', port, 'securityprox.net', 2):
        tests_passed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {tests_passed}/{tests_total} tests passed")
    print(f"{'='*60}")
    
    return 0 if tests_passed == tests_total else 1


if __name__ == "__main__":
    sys.exit(main())

