#!/usr/bin/env python3
"""
Test script for OpenFan API integration
Tests discovery and control of OpenFan devices on the network
"""

import time
import json
from typing import List
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo

class FanDiscoveryTest:
    """Test mDNS discovery for OpenFan devices"""
    
    def __init__(self):
        self.zeroconf = None
        self.browser = None
        self.discovered_fans = []
        
    def add_service(self, zeroconf, type_, name):
        """Called when a service is discovered"""
        info = zeroconf.get_service_info(type_, name)
        if info and name.startswith("uOpenFan"):
            hostname = name.split('.')[0]
            ip = None
            if info.addresses:
                ip = ".".join(map(str, info.addresses[0]))
            
            print(f"✓ Found fan: {name}")
            print(f"  Hostname: {hostname}")
            if ip:
                print(f"  IP: {ip}")
            
            self.discovered_fans.append({
                'name': name,
                'hostname': hostname,
                'ip': ip,
                'info': info
            })
    
    def remove_service(self, zeroconf, type_, name):
        """Called when a service is removed"""
        print(f"- Fan removed: {name}")
    
    def update_service(self, zeroconf, type_, name):
        """Called when a service is updated"""
        pass
    
    def discover_fans(self, timeout=5):
        """Run discovery for specified timeout"""
        print("Starting mDNS discovery for OpenFan devices...")
        print(f"Searching for _http._tcp.local. services starting with 'uOpenFan'")
        print("-" * 50)
        
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(
            self.zeroconf,
            "_http._tcp.local.",
            self
        )
        
        # Wait for discovery
        time.sleep(timeout)
        
        # Cleanup
        self.zeroconf.close()
        
        print("-" * 50)
        print(f"Discovery complete. Found {len(self.discovered_fans)} fan(s)")
        return self.discovered_fans


def test_fan_api(hostname, ip=None):
    """Test OpenFan API endpoints"""
    import requests
    
    # Use IP if available, otherwise try hostname
    if ip:
        base_url = f"http://{ip}"
    else:
        base_url = f"http://{hostname}.local"
    print(f"\nTesting OpenFan API at {base_url} ({hostname})")
    print("=" * 50)
    
    # Test 1: Get status
    print("\n1. Testing GET /api/v0/fan/status")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/status", timeout=2)
        print(f"   Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            if data.get("status") == "ok":
                print(f"   ✓ Current RPM: {data.get('rpm', 'N/A')}")
                print(f"   ✓ Current PWM: {data.get('pwm_percent', 'N/A')}%")
        else:
            print(f"   ✗ Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Set fan speed to 30%
    print("\n2. Testing SET fan speed to 30%")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/0/set?value=30", timeout=2)
        print(f"   Status code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            if data.get("status") == "ok":
                print("   ✓ Speed set successfully")
        time.sleep(2)  # Wait for fan to adjust
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Verify speed changed
    print("\n3. Verifying speed change")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   Current PWM: {data.get('pwm_percent', 'N/A')}%")
            print(f"   Current RPM: {data.get('rpm', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Set fan to 70%
    print("\n4. Testing SET fan speed to 70%")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/0/set?value=70", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("   ✓ Speed set to 70%")
        time.sleep(2)
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 5: Turn off (0%)
    print("\n5. Testing turn OFF (0%)")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/0/set?value=0", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("   ✓ Fan turned off")
        time.sleep(2)
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 6: Final status check
    print("\n6. Final status check")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            print(f"   Final PWM: {data.get('pwm_percent', 'N/A')}%")
            print(f"   Final RPM: {data.get('rpm', 'N/A')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 7: Restore to 50%
    print("\n7. Restoring to 50%")
    try:
        response = requests.get(f"{base_url}/api/v0/fan/0/set?value=50", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                print("   ✓ Fan restored to 50%")
    except Exception as e:
        print(f"   ✗ Error: {e}")


def main():
    print("OpenFan Network Discovery and API Test")
    print("=" * 70)
    
    # Step 1: Discover fans
    discovery = FanDiscoveryTest()
    fans = discovery.discover_fans(timeout=3)
    
    if not fans:
        print("\n⚠ No OpenFan devices found on the network")
        print("Make sure your OpenFan devices are powered on and connected to the network")
        return
    
    # Step 2: Test each discovered fan
    for fan in fans:
        hostname = fan['hostname']
        ip = fan.get('ip')
        test_fan_api(hostname, ip)
        print("\n" + "=" * 70)
    
    print("\nTest complete!")


if __name__ == "__main__":
    main()