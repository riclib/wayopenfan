#!/usr/bin/env python3
"""Test preset speed buttons"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from wayopenfan import ControlPopup, Fan

def main():
    app = QApplication(sys.argv)
    
    # Create popup
    popup = ControlPopup()
    
    # Create test fans
    fan1 = Fan(
        name="Left",
        ip="192.168.50.43",
        serial_number="Left-48CA43DBD6F4"
    )
    
    fan2 = Fan(
        name="Right", 
        ip="192.168.50.212",
        serial_number="Right-48CA43DBD758"
    )
    
    # Add fans
    popup.add_fan(fan1)
    popup.add_fan(fan2)
    
    # Show popup
    popup.show()
    print("Testing preset buttons...")
    
    # Test setting all fans to 50%
    def test_50():
        print("\nSetting all fans to 50%...")
        popup.set_all_fans_speed(50)
    
    QTimer.singleShot(2000, test_50)
    
    # Test setting all fans to 0% (off)
    def test_off():
        print("\nSetting all fans to OFF (0%)...")
        popup.set_all_fans_speed(0)
    
    QTimer.singleShot(4000, test_off)
    
    # Test setting all fans to 100%
    def test_100():
        print("\nSetting all fans to 100%...")
        popup.set_all_fans_speed(100)
    
    QTimer.singleShot(6000, test_100)
    
    # Quit after 8 seconds
    QTimer.singleShot(8000, app.quit)
    
    app.exec()
    print("\nTest complete!")

if __name__ == "__main__":
    main()