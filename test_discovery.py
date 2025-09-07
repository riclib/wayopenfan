#!/usr/bin/env python3
"""Test fan discovery without GUI"""

import sys
import time
from wayopenfan import FanDiscovery
from PyQt6.QtCore import QCoreApplication

def on_fan_discovered(fan):
    print(f"✓ Discovered fan: {fan.name} at {fan.ip}:{fan.port}")
    print(f"  Serial: {fan.serial_number}")
    print(f"  Status: {'ON' if fan.is_on else 'OFF'}, Speed: {fan.speed}%, RPM: {fan.rpm}")

def main():
    app = QCoreApplication(sys.argv)
    
    discovery = FanDiscovery()
    discovery.fan_discovered.connect(on_fan_discovered)
    
    print("Starting fan discovery...")
    discovery.start()
    
    # Run for 5 seconds
    QCoreApplication.processEvents()
    time.sleep(5)
    
    print("\nStopping discovery...")
    discovery.stop()
    
    print("Test complete!")

if __name__ == "__main__":
    main()