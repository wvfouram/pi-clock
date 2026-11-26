#!/bin/bash
# Installer for Clock (Windows 11 style) on Raspberry Pi
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo). It will ask for sudo when needed."
  exit 1
fi

echo "==> Installing packages"
sudo apt-get update || echo "   (apt update had errors, continuing)"
if ! sudo apt-get install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0 xdg-utils; then
  for p in python3-gi python3-gi-cairo gir1.2-gtk-3.0 xdg-utils; do
    sudo apt-get install -y "$p" || echo "   (could not install $p)"
  done
fi
sudo apt-get install -y fonts-open-sans || echo "   (Open Sans font not available, using system font)"
for p in pipewire-bin pulseaudio-utils alsa-utils; do
  sudo apt-get install -y "$p" || echo "   ($p not available, skipping)"
done

echo "==> Installing app"
sudo install -d /opt/pi-clock
sudo install -m 644 "$SRC/pi_clock.py" /opt/pi-clock/pi_clock.py
printf '#!/bin/sh\nexec /usr/bin/python3 /opt/pi-clock/pi_clock.py "$@"\n' | sudo tee /usr/local/bin/pi-clock >/dev/null
sudo chmod 755 /usr/local/bin/pi-clock

echo "==> Adding menu entry and icon"
sudo install -D -m 644 "$SRC/pi-clock.svg" /usr/share/icons/hicolor/scalable/apps/pi-clock.svg
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
sudo tee /usr/share/applications/pi-clock.desktop >/dev/null <<'DESK'
[Desktop Entry]
Type=Application
Name=Clock
GenericName=Clock
Comment=Alarms, timers, stopwatch, world clock and focus sessions
Exec=pi-clock 
Icon=pi-clock
Terminal=false
Categories=Utility;Clock;GTK;
StartupWMClass=pi-clock
StartupNotify=true
DESK
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true

echo "==> Letting alarms and timers work in the background"
mkdir -p "$HOME/.config/autostart"
printf '[Desktop Entry]\nType=Application\nName=Clock (alarms)\nExec=pi-clock --background\nNoDisplay=true\n' > "$HOME/.config/autostart/pi-clock.desktop"
pkill -f /opt/pi-clock/pi_clock.py 2>/dev/null || true
if [ -n "$WAYLAND_DISPLAY" ] || [ -n "$DISPLAY" ]; then
  (setsid pi-clock --background >/dev/null 2>&1 &)
fi

echo
echo "Done. Open Clock from the menu or run: pi-clock"
