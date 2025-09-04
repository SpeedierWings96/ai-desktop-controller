#!/usr/bin/env bash
set -e

# Default env
: ${DISPLAY:=:1}
: ${VNC_PORT:=5901}
: ${NOVNC_PORT:=8080}
: ${RESOLUTION:=1920x1080}
: ${DEPTH:=24}
: ${VNC_PASSWORD:=changeme}

# Setup VNC xstartup for XFCE
mkdir -p /root/.vnc
cat >/root/.vnc/xstartup <<'EOF'
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
export XDG_RUNTIME_DIR="/run/user/0"
startxfce4 &
EOF
chmod +x /root/.vnc/xstartup

# Ensure no stale vncserver lock
vncserver -kill ${DISPLAY} >/dev/null 2>&1 || true
rm -rf /tmp/.X*-lock /tmp/.X11-unix/X*

# Start supervisor to bring up VNC, noVNC, XFCE, and the app
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf


