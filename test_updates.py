#!/usr/bin/env python3
"""Test update mechanism"""

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
    
    QTimer.singleShot(3000, show_popup)
    
    # Quit after 8 seconds
    QTimer.singleShot(8000, app.quit)
    
    app.exec()

if __name__ == "__main__":
    main()