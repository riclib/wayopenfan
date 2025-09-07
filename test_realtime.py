#!/usr/bin/env python3
"""Test real-time updates functionality"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from wayopenfan import ControlPopup, Fan

def main():
    app = QApplication(sys.argv)
    
    # Create test popup
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
    
    # Add fans to popup
    popup.add_fan(fan1)
    popup.add_fan(fan2)
    
    # Show popup (this should trigger updates)
    popup.show()
    print("Popup shown - real-time updates should start (every 0.5s)")
    
    # Run for 5 seconds
    def check_status():
        print(f"\nStatus after updates:")
        for serial, fan in popup.fans.items():
            print(f"  {fan.name}: Speed={fan.speed}%, RPM={fan.rpm}, On={fan.is_on}")
    
    # Check status after 3 seconds
    QTimer.singleShot(3000, check_status)
    
    # Hide after 4 seconds to test stop
    def hide_popup():
        print("\nHiding popup - updates should stop")
        popup.hide()
    
    QTimer.singleShot(4000, hide_popup)
    
    # Quit after 5 seconds
    QTimer.singleShot(5000, app.quit)
    
    app.exec()
    print("\nTest complete!")

if __name__ == "__main__":
    main()