#!/usr/bin/env python3
"""
WayOpenFan - System tray application for controlling OpenFan devices on Wayland/Hyprland
"""

import os
import sys
import json
import threading

# Suppress Qt style warnings
os.environ.pop('QT_STYLE_OVERRIDE', None)
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import requests
import requests.adapters
from zeroconf import ServiceBrowser, Zeroconf, ServiceInfo
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget, QPushButton,
    QSlider, QLabel, QHBoxLayout, QVBoxLayout, QCheckBox, QFrame,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint, QRect, QThread, pyqtSlot, QEvent
from PyQt6.QtGui import QIcon, QAction, QCursor, QScreen, QPalette, QColor, QMouseEvent


class APIWorker(QThread):
    """Worker thread for API calls to avoid blocking UI"""
    result_ready = pyqtSignal(str, bool, int, int)  # serial, is_on, speed, rpm
    
    def __init__(self, fan, operation, value=None):
        super().__init__()
        self.fan = fan
        self.operation = operation
        self.value = value
        
    def run(self):
        """Execute API call in thread"""
        try:
            if self.operation == 'toggle':
                success = self.fan.toggle()
                if success:
                    self.result_ready.emit(self.fan.serial_number, self.fan.is_on, self.fan.speed, self.fan.rpm)
            elif self.operation == 'speed':
                success = self.fan.set_speed(self.value)
                if success:
                    self.result_ready.emit(self.fan.serial_number, self.fan.is_on, self.fan.speed, self.fan.rpm)
            elif self.operation == 'power':
                success = self.fan.set_power(self.value)
                if success:
                    self.result_ready.emit(self.fan.serial_number, self.fan.is_on, self.fan.speed, self.fan.rpm)
            elif self.operation == 'status':
                # Create a temporary fan copy to avoid modifying the shared object
                temp_fan = Fan(
                    name=self.fan.name,
                    ip=self.fan.ip,
                    serial_number=self.fan.serial_number,
                    port=self.fan.port
                )
                # Get status on the copy
                temp_fan.get_status()
                # Emit the new values
                self.result_ready.emit(temp_fan.serial_number, temp_fan.is_on, temp_fan.speed, temp_fan.rpm)
        except Exception as e:
            print(f"API Worker error: {e}")


@dataclass
class Fan:
    """Represents an OpenFan device"""
    name: str
    ip: str  # Use IP address directly
    serial_number: str
    port: int = 80
    is_on: bool = False
    speed: int = 50  # PWM percentage 0-100
    rpm: int = 0
    last_speed: int = 50  # Remember last speed for toggle
    _session: Optional[requests.Session] = field(default=None, init=False, repr=False, compare=False)
    
    @property
    def base_url(self) -> str:
        return f"http://{self.ip}:{self.port}"
    
    @property
    def session(self) -> requests.Session:
        """Get or create a session for connection pooling"""
        if self._session is None:
            self._session = requests.Session()
            # Set adapter with connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=1,
                pool_maxsize=2,
                max_retries=1
            )
            self._session.mount('http://', adapter)
        return self._session
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Get current fan status"""
        try:
            response = self.session.get(f"{self.base_url}/api/v0/fan/status", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.rpm = data.get("rpm", 0)
                    self.speed = data.get("pwm_percent", 0)
                    self.is_on = self.speed > 0
                    if self.is_on:
                        self.last_speed = self.speed
                    return data
        except Exception as e:
            print(f"Error getting status for {self.name}: {e}")
        return None
    
    def get_friendly_name(self) -> str:
        """Get the friendly name for the fan"""
        # Remove uOpenFan prefix if present
        if self.name.startswith("uOpenFan-"):
            return self.name.replace("uOpenFan-", "")
        return self.name if self.name else f"Fan {self.serial_number[-4:]}"
    
    def set_speed(self, speed: int) -> bool:
        """Set fan speed (0-100%)"""
        try:
            # Clamp speed to valid range
            speed = max(0, min(100, speed))
            
            response = self.session.get(
                f"{self.base_url}/api/v0/fan/0/set",
                params={"value": speed},
                timeout=3
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.speed = speed
                    self.is_on = speed > 0
                    if self.is_on:
                        self.last_speed = speed
                    return True
        except Exception as e:
            print(f"Error setting speed for {self.name}: {e}")
        return False
    
    def set_power(self, on: bool) -> bool:
        """Turn fan on/off"""
        if on:
            # Turn on to last known speed or default
            return self.set_speed(self.last_speed if self.last_speed > 0 else 50)
        else:
            # Turn off (speed 0)
            return self.set_speed(0)
    
    def toggle(self) -> bool:
        """Toggle fan on/off"""
        return self.set_power(not self.is_on)


class FanDiscovery(QObject):
    """Discovers OpenFan devices on the network using mDNS"""
    
    fan_discovered = pyqtSignal(Fan)
    fan_removed = pyqtSignal(str)  # serial number
    
    def __init__(self):
        super().__init__()
        self.zeroconf = None
        self.browser = None
        self.fans: Dict[str, Fan] = {}
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def start(self):
        """Start discovery service"""
        self.zeroconf = Zeroconf()
        self.browser = ServiceBrowser(
            self.zeroconf,
            "_http._tcp.local.",
            self
        )
        print("Started OpenFan discovery service")
    
    def stop(self):
        """Stop discovery service"""
        if self.zeroconf:
            self.zeroconf.close()
            self.zeroconf = None
            self.browser = None
        self.executor.shutdown(wait=False)
        print("Stopped OpenFan discovery service")
    
    def add_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Called when a new service is discovered"""
        self.executor.submit(self._process_service_async, zeroconf, type_, name)
    
    def update_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated"""
        self.executor.submit(self._process_service_async, zeroconf, type_, name)
    
    def remove_service(self, zeroconf: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed"""
        # Check if it's an OpenFan device
        if name.startswith("uOpenFan"):
            # Extract serial from hostname
            hostname = name.split('.')[0]
            serial = hostname.replace("uOpenFan-", "")
            if serial in self.fans:
                del self.fans[serial]
                self.fan_removed.emit(serial)
                print(f"Fan removed: {serial}")
    
    def _process_service_async(self, zeroconf: Zeroconf, type_: str, name: str):
        """Process service info in thread pool"""
        info = zeroconf.get_service_info(type_, name)
        if info:
            self._process_service(info)
    
    def _process_service(self, info: ServiceInfo) -> None:
        """Process discovered service info"""
        # Check if it's an OpenFan device
        if not info.name.startswith("uOpenFan"):
            return
            
        if info.addresses:
            ip = ".".join(map(str, info.addresses[0]))
            port = info.port if info.port else 80
            
            # Extract hostname and serial from service name
            hostname = info.name.split('.')[0]
            serial = hostname.replace("uOpenFan-", "")
            
            if serial and serial not in self.fans:
                # Extract fan name
                name = serial.split('-')[0] if '-' in serial else serial
                
                fan = Fan(
                    name=name,
                    ip=ip,
                    port=port,
                    serial_number=serial
                )
                
                # Get initial status
                fan.get_status()
                
                # Get friendly name
                friendly_name = fan.get_friendly_name()
                fan.name = friendly_name
                
                self.fans[serial] = fan
                self.fan_discovered.emit(fan)
                print(f"Discovered Fan: {friendly_name} at {ip}:{port}")


class FanControlWidget(QWidget):
    """Widget for controlling a single fan"""
    
    def __init__(self, fan: Fan, parent=None):
        super().__init__(parent)
        self.fan = fan
        self.api_worker = None
        self.speed_timer = None
        self.pending_speed = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        # Header with checkbox and name
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Power checkbox
        self.power_checkbox = QCheckBox()
        self.power_checkbox.setChecked(self.fan.is_on)
        self.power_checkbox.stateChanged.connect(self.on_power_changed)
        header_layout.addWidget(self.power_checkbox)
        
        # Fan name
        self.name_label = QLabel(self.fan.name)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.name_label)
        header_layout.addStretch()
        
        # RPM display
        self.rpm_label = QLabel(f"{self.fan.rpm} RPM")
        self.rpm_label.setStyleSheet("color: #808080; font-size: 10px;")
        header_layout.addWidget(self.rpm_label)
        
        layout.addLayout(header_layout)
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(8)
        
        # Speed icon/label
        speed_label = QLabel("🌀")
        speed_label.setFixedWidth(20)
        speed_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(0)
        self.speed_slider.setMaximum(100)
        self.speed_slider.setValue(self.fan.speed)
        self.speed_slider.setFixedHeight(20)
        # Enable jump-to-position on click
        self.speed_slider.setPageStep(1)
        self.speed_slider.setSingleStep(1)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        # Install event filter for click-to-position
        self.speed_slider.installEventFilter(self)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_value = QLabel(f"{self.fan.speed}%")
        self.speed_value.setFixedWidth(35)
        self.speed_value.setAlignment(Qt.AlignmentFlag.AlignRight)
        speed_layout.addWidget(self.speed_value)
        
        layout.addLayout(speed_layout)
        
        self.setLayout(layout)
        
    def on_power_changed(self, state):
        """Handle power checkbox change"""
        is_on = state == Qt.CheckState.Checked.value
        # Run in thread
        self.api_worker = APIWorker(self.fan, 'power', is_on)
        self.api_worker.result_ready.connect(self.on_api_result)
        self.api_worker.start()
        
    def on_speed_changed(self, value):
        """Handle speed slider change with heavy throttling"""
        self.speed_value.setText(f"{value}%")
        self.pending_speed = value
        
        # Cancel previous timer if it exists
        if self.speed_timer:
            self.speed_timer.stop()
            self.speed_timer = None
            
        # Create new timer with longer delay for dragging
        self.speed_timer = QTimer()
        self.speed_timer.setSingleShot(True)
        self.speed_timer.timeout.connect(self.apply_pending_speed)
        self.speed_timer.start(500)  # 500ms delay
        
    def apply_pending_speed(self):
        """Apply the pending speed change"""
        if self.pending_speed is not None:
            self.api_worker = APIWorker(self.fan, 'speed', self.pending_speed)
            self.api_worker.result_ready.connect(self.on_api_result)
            self.api_worker.start()
            self.pending_speed = None
            
    @pyqtSlot(str, bool, int, int)
    def on_api_result(self, serial, is_on, speed, rpm):
        """Handle API result from worker thread"""
        if serial == self.fan.serial_number:
            self.fan.is_on = is_on
            self.fan.speed = speed
            self.fan.rpm = rpm
            self.update_state()
        
    def update_state(self):
        """Update widget to reflect current fan state"""
        self.power_checkbox.blockSignals(True)
        self.power_checkbox.setChecked(self.fan.is_on)
        self.power_checkbox.blockSignals(False)
        
        self.rpm_label.setText(f"{self.fan.rpm} RPM")
        
        if self.pending_speed is None:  # Only update if not currently dragging
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(self.fan.speed)
            self.speed_value.setText(f"{self.fan.speed}%")
            self.speed_slider.blockSignals(False)
        
    def update_name(self, name: str):
        """Update the fan name label"""
        self.name_label.setText(name)
    
    def eventFilter(self, source, event):
        """Event filter to handle click-to-position on slider"""
        if source == self.speed_slider and event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent):
                # Calculate position as percentage
                click_x = event.position().x()
                slider_width = self.speed_slider.width()
                
                # Calculate the value based on click position
                if slider_width > 0:
                    # Account for slider handle width (roughly 12px)
                    effective_width = slider_width - 12
                    adjusted_x = max(0, min(click_x - 6, effective_width))
                    
                    # Calculate percentage and map to slider range
                    percentage = adjusted_x / effective_width
                    min_val = self.speed_slider.minimum()
                    max_val = self.speed_slider.maximum()
                    new_value = int(min_val + (max_val - min_val) * percentage)
                    
                    # Set the value directly
                    self.speed_slider.setValue(new_value)
                    return True  # Event handled
                    
        return super().eventFilter(source, event)


class ControlPopup(QWidget):
    """Popup window for light controls"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fan_widgets: Dict[str, FanControlWidget] = {}
        self.fans: Dict[str, Fan] = {}  # Store fan references
        self.update_timer = None
        self.update_workers = []
        self.setup_ui()
        
        # Set window title for identification
        self.setWindowTitle("WayOpenFan Controls")
        
        # Window flags for floating overlay
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        
        # Make it a tooltip-style window for Wayland
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
    def setup_ui(self):
        # Main container with background
        container = QWidget()
        container.setObjectName("container")
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(8)
        
        # Title with lightbulb icon
        title = QLabel("🌀 WayOpenFan")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(title)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        self.main_layout.addWidget(line)
        
        # Container for light controls
        self.fans_layout = QVBoxLayout()
        self.fans_layout.setSpacing(6)
        self.main_layout.addLayout(self.fans_layout)
        
        # No lights message
        self.no_fans_label = QLabel("No fans found")
        self.no_fans_label.setObjectName("no_fans")
        self.no_fans_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fans_layout.addWidget(self.no_fans_label)
        
        # Bottom buttons - more compact
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        refresh_button = QPushButton("↻")
        refresh_button.setObjectName("refresh_btn")
        refresh_button.setFixedSize(28, 24)
        refresh_button.setToolTip("Refresh")
        refresh_button.clicked.connect(self.refresh_requested)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        
        close_button = QPushButton("✕")
        close_button.setObjectName("close_btn")
        close_button.setFixedSize(28, 24)
        close_button.setToolTip("Close")
        close_button.clicked.connect(self.hide)
        button_layout.addWidget(close_button)
        
        self.main_layout.addLayout(button_layout)
        
        container.setLayout(self.main_layout)
        
        # Outer layout for the transparent window
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(container)
        self.setLayout(outer_layout)
        
        # Dark theme styling
        self.setStyleSheet("""
            #container {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
            
            #title {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            
            #separator {
                background-color: #3c3c3c;
                max-height: 1px;
            }
            
            QLabel {
                color: #e0e0e0;
            }
            
            #no_fans {
                color: #808080;
                padding: 15px;
            }
            
            QCheckBox {
                color: #e0e0e0;
                spacing: 5px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #606060;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border-color: #14b8a6;
            }
            
            QSlider::groove:horizontal {
                height: 4px;
                background: #3c3c3c;
                border-radius: 2px;
            }
            
            QSlider::handle:horizontal {
                width: 12px;
                height: 12px;
                background: #14b8a6;
                border-radius: 6px;
                margin: -4px 0;
            }
            
            QSlider::sub-page:horizontal {
                background: #0d7377;
                border-radius: 2px;
            }
            
            QPushButton {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 2px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #3c3c3c;
                border-color: #4c4c4c;
            }
            
            QPushButton:pressed {
                background-color: #252525;
            }
            
            #refresh_btn, #close_btn {
                font-size: 14px;
            }
        """)
        
        # Set fixed size to prevent stretching
        self.setFixedWidth(280)
        self.setMaximumHeight(400)  # Prevent vertical stretching
        
    def add_fan(self, fan: Fan):
        """Add a fan control widget"""
        if fan.serial_number not in self.fan_widgets:
            # Remove "no fans" label if this is the first fan
            if len(self.fan_widgets) == 0:
                self.no_fans_label.setVisible(False)
                
            widget = FanControlWidget(fan)
            self.fan_widgets[fan.serial_number] = widget
            self.fans[fan.serial_number] = fan  # Store fan reference
            
            # Add separator between fans
            if len(self.fan_widgets) > 1:
                separator = QFrame()
                separator.setFrameShape(QFrame.Shape.HLine)
                separator.setObjectName("fan_separator")
                separator.setStyleSheet("background-color: #2d2d2d; max-height: 1px;")
                self.fans_layout.addWidget(separator)
                
            self.fans_layout.addWidget(widget)
            
    def remove_fan(self, serial: str):
        """Remove a fan control widget"""
        if serial in self.fan_widgets:
            widget = self.fan_widgets[serial]
            self.fans_layout.removeWidget(widget)
            widget.deleteLater()
            del self.fan_widgets[serial]
            if serial in self.fans:
                del self.fans[serial]
            
            # Show "no fans" label if no fans remain
            if len(self.fan_widgets) == 0:
                self.no_fans_label.setVisible(True)
                
    def update_fan(self, fan: Fan):
        """Update a fan control widget"""
        if fan.serial_number in self.fan_widgets:
            self.fans[fan.serial_number] = fan  # Update stored fan reference
            self.fan_widgets[fan.serial_number].update_state()
            
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        # Note: Window positioning doesn't work on Wayland
        # Position is controlled by Hyprland window rules instead
        
        # Start real-time updates when window is shown
        self.start_updates()
        
        # Update all fan states immediately
        for widget in self.fan_widgets.values():
            widget.update_state()
            
    def hideEvent(self, event):
        """Handle hide event"""
        super().hideEvent(event)
        # Stop real-time updates when window is hidden
        self.stop_updates()
    
    def start_updates(self):
        """Start real-time fan status updates"""
        if not self.update_timer:
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_all_fans)
            self.update_timer.start(1000)  # Update every 1 second
    
    def stop_updates(self):
        """Stop real-time fan status updates"""
        if self.update_timer:
            self.update_timer.stop()
            self.update_timer = None
        # Clean up any running workers
        self.update_workers = [w for w in self.update_workers if w.isRunning()]
    
    def update_all_fans(self):
        """Update status for all fans"""
        for fan in self.fans.values():
            # Skip if a worker is already running for this fan
            if not any(w.isRunning() and w.fan.serial_number == fan.serial_number 
                      for w in self.update_workers):
                worker = APIWorker(fan, 'status')
                worker.result_ready.connect(self.on_status_update)
                worker.start()
                self.update_workers.append(worker)
    
    @pyqtSlot(str, bool, int, int)
    def on_status_update(self, serial, is_on, speed, rpm):
        """Handle status update from worker"""
        if serial in self.fans:
            fan = self.fans[serial]
            # Only update if values changed
            if fan.is_on != is_on or fan.speed != speed or fan.rpm != rpm:
                fan.is_on = is_on
                fan.speed = speed
                fan.rpm = rpm
                if serial in self.fan_widgets:
                    self.fan_widgets[serial].update_state()
        
        # Clean up finished workers
        self.update_workers = [w for w in self.update_workers if w.isRunning()]
    
    def refresh_requested(self):
        """Signal that refresh was requested"""
        pass
    
    def mousePressEvent(self, event):
        """Allow dragging the window"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)


class WayOpenFanTray(QSystemTrayIcon):
    """System tray application for controlling OpenFan devices"""
    
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.fans: Dict[str, Fan] = {}
        self.update_workers = []
        
        # Create popup window
        self.popup = ControlPopup()
        self.popup.refresh_requested = self.refresh_fans
        
        # Setup discovery
        self.discovery = FanDiscovery()
        self.discovery.fan_discovered.connect(self.on_fan_discovered)
        self.discovery.fan_removed.connect(self.on_fan_removed)
        
        # Setup UI
        self.setup_tray_icon()
        self.create_menu()
        
        # Connect left-click to show popup
        self.activated.connect(self.on_tray_activated)
        
        # Setup update timer with longer interval
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_fan_states)
        self.update_timer.start(10000)  # Update every 10 seconds instead of 5
        
        # Start discovery
        self.discovery.start()
        
    def setup_tray_icon(self):
        """Setup system tray icon"""
        # Try to load custom icon first
        import os
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fan-icon.svg")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # Fallback to system icons
            icon = QIcon.fromTheme("preferences-desktop-display")
            if icon.isNull():
                icon = self.app.style().standardIcon(self.app.style().StandardPixmap.SP_ComputerIcon)
        
        self.setIcon(icon)
        self.setToolTip("WayOpenFan - Click to control")
        self.show()
        
    def create_menu(self):
        """Create the right-click context menu"""
        menu = QMenu()
        
        # Open controls action
        open_action = menu.addAction("Open Controls")
        open_action.triggered.connect(self.show_popup)
        
        # Refresh action
        refresh_action = menu.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh_fans)
        
        # Quit action
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        
        self.setContextMenu(menu)
        
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left click
            self.show_popup()
        
    def show_popup(self):
        """Show the control popup"""
        if self.popup.isVisible():
            self.popup.hide()
        else:
            self.popup.show()
            self.popup.raise_()
            self.popup.activateWindow()
            
    def on_fan_discovered(self, fan: Fan):
        """Handle new fan discovery"""
        self.fans[fan.serial_number] = fan
        self.popup.add_fan(fan)
        
    def on_fan_removed(self, serial: str):
        """Handle fan removal"""
        if serial in self.fans:
            del self.fans[serial]
            self.popup.remove_fan(serial)
            
    def update_fan_states(self):
        """Periodically update fan states in background"""
        for fan in self.fans.values():
            worker = APIWorker(fan, 'status')
            worker.result_ready.connect(self.on_status_update)
            worker.start()
            self.update_workers.append(worker)
            
    @pyqtSlot(str, bool, int, int)
    def on_status_update(self, serial, is_on, speed, rpm):
        """Handle status update from worker"""
        if serial in self.fans:
            fan = self.fans[serial]
            if fan.is_on != is_on or fan.speed != speed or fan.rpm != rpm:
                fan.is_on = is_on
                fan.speed = speed
                fan.rpm = rpm
                self.popup.update_fan(fan)
        
        # Clean up finished workers
        self.update_workers = [w for w in self.update_workers if w.isRunning()]
                
    def refresh_fans(self):
        """Manually refresh fan discovery"""
        self.discovery.stop()
        self.discovery.start()
        
    def quit_application(self):
        """Quit the application"""
        self.discovery.stop()
        self.popup.close()
        self.app.quit()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set application identity for Wayland
    app.setApplicationName("WayOpenFan")
    app.setOrganizationName("WayOpenFan")
    app.setDesktopFileName("wayopenfan")  # This sets the Wayland app_id
    
    # Force Fusion style and dark palette
    app.setStyle("Fusion")
    
    # Create system tray
    tray = WayOpenFanTray(app)
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()