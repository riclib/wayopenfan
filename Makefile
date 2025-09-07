.PHONY: setup run install uninstall clean help

INSTALL_DIR := $(HOME)/.local/share/wayopenfan
DESKTOP_DIR := $(HOME)/.local/share/applications
AUTOSTART_DIR := $(HOME)/.config/autostart

help:
	@echo "WayOpenFan - OpenFan Controller for Wayland"
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Create virtual environment and install dependencies"
	@echo "  run         - Run the application"
	@echo "  install     - Install to ~/.local/share/wayopenfan"
	@echo "  uninstall   - Remove installation"
	@echo "  autostart   - Enable autostart on login"
	@echo "  clean       - Remove virtual environment"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup && make run"

setup:
	@echo "Setting up WayOpenFan..."
	@chmod +x setup.sh
	@./setup.sh

run: 
	@if [ ! -d "venv" ]; then \
		echo "Virtual environment not found. Running setup first..."; \
		$(MAKE) setup; \
	fi
	@chmod +x run.sh
	@./run.sh

install: setup
	@echo "Installing WayOpenFan to $(INSTALL_DIR)..."
	@mkdir -p $(INSTALL_DIR)
	@mkdir -p $(DESKTOP_DIR)
	
	# Copy application files
	@cp -r venv $(INSTALL_DIR)/
	@cp wayopenfan.py $(INSTALL_DIR)/
	@cp run.sh $(INSTALL_DIR)/
	@cp requirements.txt $(INSTALL_DIR)/
	@cp icon.svg $(INSTALL_DIR)/
	
	# Create desktop entry with correct path
	@echo "[Desktop Entry]" > $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Type=Application" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Name=WayOpenFan" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Comment=Control Elgato Key Lights from system tray" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Exec=$(INSTALL_DIR)/run.sh" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Icon=preferences-desktop-display" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Terminal=false" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "Categories=Utility;" >> $(DESKTOP_DIR)/wayopenfan.desktop
	@echo "StartupNotify=false" >> $(DESKTOP_DIR)/wayopenfan.desktop
	
	@chmod +x $(INSTALL_DIR)/run.sh
	@chmod +x $(INSTALL_DIR)/wayopenfan.py
	
	@echo "Installation complete!"
	@echo "You can now:"
	@echo "  - Run from terminal: $(INSTALL_DIR)/run.sh"
	@echo "  - Find it in your application menu"
	@echo "  - Enable autostart: make autostart"

uninstall:
	@echo "Uninstalling WayOpenFan..."
	@rm -rf $(INSTALL_DIR)
	@rm -f $(DESKTOP_DIR)/wayopenfan.desktop
	@rm -f $(AUTOSTART_DIR)/wayopenfan.desktop
	@echo "Uninstall complete!"

autostart:
	@echo "Enabling autostart..."
	@mkdir -p $(AUTOSTART_DIR)
	
	@if [ -f "$(INSTALL_DIR)/run.sh" ]; then \
		cp $(DESKTOP_DIR)/wayopenfan.desktop $(AUTOSTART_DIR)/; \
		echo "Autostart enabled!"; \
	else \
		echo "Please run 'make install' first"; \
		exit 1; \
	fi

clean:
	@echo "Cleaning up..."
	@rm -rf venv
	@rm -rf __pycache__
	@rm -f *.pyc
	@echo "Clean complete!"