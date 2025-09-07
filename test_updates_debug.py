#!/usr/bin/env python3
"""Test update mechanism with debug output"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from wayopenfan import WayOpenFanTray

def main():
    app = QApplication(sys.argv)
    
    # Create tray
    tray = WayOpenFanTray(app)
    
    # Wait for discovery
    QTimer.singleShot(2000, lambda: print(f"Fans discovered: {len(tray.fans)}"))
    
    # Show popup after 3 seconds
    def show_popup():
        print("Showing popup...")
        tray.show_popup()
        print(f"Popup has {len(tray.popup.fans)} fans")
        print(f"Update timer active: {tray.popup.update_timer is not None}")
        if tray.popup.update_timer:
            print(f"Update timer is running: {tray.popup.update_timer.isActive()}")
    
    QTimer.singleShot(3000, show_popup)
    
    # Check update status periodically
    def check_updates():
        if hasattr(tray.popup, 'update_timer') and tray.popup.update_timer:
            print(f"Timer active: {tray.popup.update_timer.isActive()}")
            for serial, fan in tray.popup.fans.items():
                print(f"  {fan.name}: speed={fan.speed}%, rpm={fan.rpm}")
    
    timer = QTimer()
    timer.timeout.connect(check_updates)
    timer.start(1000)
    
    # Quit after 10 seconds
    QTimer.singleShot(10000, app.quit)
    
    app.exec()

if __name__ == "__main__":
    main()