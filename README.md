# WayOpenFan

A system tray application for controlling OpenFan devices on Wayland/Hyprland desktop environments.

## Features

- 🌀 **System Tray Integration**: Clean integration with your desktop environment
- 🔍 **Auto-Discovery**: Automatically discovers OpenFan devices on your network via mDNS
- 🎛️ **Speed Control**: Smooth fan speed control from 0-100% with live RPM display
- 🖱️ **Easy Access**: Single-click popup for quick fan control
- 🎨 **Dark Theme**: Modern dark theme that fits well with most desktop environments
- ⚡ **Real-time Updates**: Live RPM and status updates

## Prerequisites

- Python 3.8+
- PyQt6
- OpenFan devices on your network
- Wayland compositor (tested with Hyprland)

## Installation

### Quick Install

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wayopenfan.git
cd wayopenfan
```

2. Run the setup script:
```bash
./setup.sh
```

3. Launch the application:
```bash
./run.sh
```

### Manual Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python wayopenfan.py
```

## System Installation

To install WayOpenFan system-wide:

```bash
sudo make install
```

To uninstall:

```bash
sudo make uninstall
```

## Hyprland Configuration

For optimal window behavior in Hyprland, add the provided window rules to your config:

```bash
cat hyprland-wayopenfan.conf >> ~/.config/hypr/hyprland.conf
```

For ultrawide monitors, use:

```bash
cat hyprland-wayopenfan-ultrawide.conf >> ~/.config/hypr/hyprland.conf
```

## Usage

1. **Launch**: Start WayOpenFan from your application menu or run `wayopenfan` in terminal
2. **Access Controls**: Click the system tray icon to open the control popup
3. **Control Fans**: 
   - Toggle fans on/off with the checkbox
   - Adjust speed with the slider (0-100%)
   - View current RPM in real-time
4. **Right-click Menu**: Right-click the tray icon for additional options

## OpenFan API

WayOpenFan communicates with OpenFan devices using their HTTP API:

- **Status**: `GET /api/v0/fan/status` - Returns current RPM and PWM percentage
- **Set Speed**: `GET /api/v0/fan/0/set?value={0-100}` - Sets fan speed

## Troubleshooting

### Fans Not Discovered

- Ensure OpenFan devices are powered on and connected to the network
- Check that mDNS is working: `avahi-browse -a | grep uOpenFan`
- Verify network connectivity to the fans

### UI Issues on Wayland

- Ensure `QT_QPA_PLATFORM=wayland` is set
- Check that PyQt6 is installed with Wayland support
- Verify Hyprland window rules are properly configured

## Development

### Project Structure

```
wayopenfan/
├── wayopenfan.py          # Main application
├── test_fan_api.py        # API testing utility
├── fan-icon.svg           # Application icon
├── requirements.txt       # Python dependencies
├── Makefile              # Installation scripts
└── hyprland-*.conf       # Window manager configs
```

### Testing

Run the test utility to verify fan communication:

```bash
python test_fan_api.py
```

## License

MIT License - See LICENSE file for details

## Credits

Based on the WayKeyLight architecture for Elgato Key Lights, adapted for OpenFan devices.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.