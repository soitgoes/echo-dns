#!/usr/bin/env python3
"""
Simple test script for the DNS server functionality.
"""

import json
import os
from dns_server import SimpleDNSServer


def test_ip_validation():
    """Test IP address validation."""
    print("Testing IP validation...")
    
    # Create a temporary server instance for testing
    server = SimpleDNSServer()
    
    # Valid IPs
    valid_ips = ["192.168.1.1", "10.0.0.1", "127.0.0.1", "8.8.8.8", "0.0.0.0"]
    for ip in valid_ips:
        result = server.is_valid_ip(ip)
        print(f"✓ {ip} -> {result}")
        assert result, f"{ip} should be valid"
    
    # Invalid IPs
    invalid_ips = ["999.999.999.999", "256.1.1.1", "192.168.1", "not-an-ip", "192.168.1.1.1"]
    for ip in invalid_ips:
        result = server.is_valid_ip(ip)
        print(f"✓ {ip} -> {result}")
        assert not result, f"{ip} should be invalid"
    
    print("IP validation tests passed!\n")


def test_domain_parsing():
    """Test domain parsing logic."""
    print("Testing domain parsing...")
    
    # Create test config
    test_config = {
        "domain": "testdomain.com",
        "port": 5353,
        "host": "127.0.0.1"
    }
    
    with open("test_config.json", "w") as f:
        json.dump(test_config, f)
    
    server = SimpleDNSServer("test_config.json")
    
    # Test cases
    test_cases = [
        ("192-168-1-1.testdomain.com", "192.168.1.1", True),
        ("10-0-0-1.testdomain.com", "10.0.0.1", True),
        ("999-999-999-999.testdomain.com", "999.999.999.999", False),
        ("192-168-1-1.wrongdomain.com", None, False),
        ("not-an-ip.testdomain.com", "not.an.ip", False),
    ]
    
    for domain, expected_ip, should_be_valid in test_cases:
        # Extract subdomain
        if domain.endswith('.' + server.config['domain']):
            subdomain = domain[:-len('.' + server.config['domain'])]
            potential_ip = subdomain.replace('-', '.')
            is_valid = server.is_valid_ip(potential_ip)
            
            print(f"✓ {domain} -> {potential_ip} (valid: {is_valid})")
            
            if should_be_valid:
                assert is_valid, f"{domain} should be valid"
                assert potential_ip == expected_ip, f"Expected {expected_ip}, got {potential_ip}"
            else:
                assert not is_valid, f"{domain} should be invalid"
        else:
            print(f"✓ {domain} -> wrong domain")
    
    # Clean up
    if os.path.exists("test_config.json"):
        os.remove("test_config.json")
    
    print("Domain parsing tests passed!\n")


def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")
    
    # Test default config creation
    if os.path.exists("config.json"):
        os.remove("config.json")
    
    server = SimpleDNSServer()
    assert server.config["domain"] == "somedomain.com"
    assert server.config["port"] == 53
    assert server.config["host"] == "0.0.0.0"
    print("✓ Default config loaded correctly")
    
    # Test custom config
    custom_config = {
        "domain": "customdomain.com",
        "port": 5353,
        "host": "127.0.0.1"
    }
    
    with open("custom_config.json", "w") as f:
        json.dump(custom_config, f)
    
    server2 = SimpleDNSServer("custom_config.json")
    assert server2.config["domain"] == "customdomain.com"
    assert server2.config["port"] == 5353
    assert server2.config["host"] == "127.0.0.1"
    print("✓ Custom config loaded correctly")
    
    # Clean up
    if os.path.exists("custom_config.json"):
        os.remove("custom_config.json")
    
    print("Configuration tests passed!\n")


def main():
    """Run all tests."""
    print("Running DNS Server Tests\n")
    print("=" * 50)
    
    try:
        test_ip_validation()
        test_domain_parsing()
        test_config_loading()
        
        print("=" * 50)
        print("All tests passed! ✓")
        print("\nTo run the server:")
        print("  python3 dns_server.py")
        print("\nTo test with dig:")
        print("  dig @localhost 192-168-1-1.somedomain.com")
        
    except Exception as e:
        print(f"Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
