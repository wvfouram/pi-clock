#!/bin/bash
# Removes Clock.
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo)."
  exit 1
fi
pkill -f /opt/pi-clock/pi_clock.py 2>/dev/null || true
rm -f "$HOME/.config/autostart/pi-clock.desktop"
rm -rf "$HOME/.cache/pi-clock"

sudo rm -rf /opt/pi-clock /usr/local/bin/pi-clock /usr/share/applications/pi-clock.desktop \
  /usr/share/icons/hicolor/scalable/apps/pi-clock.svg
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Clock removed. Your settings are still in ~/.config/pi-clock (delete that folder to remove them)."
