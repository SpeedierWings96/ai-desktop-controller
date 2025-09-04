# Linux desktop container with XFCE, TigerVNC, noVNC, and Supervisor
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DISPLAY=:1 \
    VNC_PORT=5901 \
    NOVNC_PORT=8080 \
    RESOLUTION=1920x1080 \
    DEPTH=24 \
    VNC_PASSWORD=changeme

# Base packages and desktop stack
RUN apt-get update && apt-get install -y --no-install-recommends \
    xfce4 xfce4-terminal xfce4-session \
    tigervnc-standalone-server tigervnc-common \
    novnc websockify \
    supervisor \
    dbus-x11 x11-xserver-utils \
    xdotool wmctrl scrot \
    python3 python3-pip \
    build-essential gcc g++ make \
    python3-dev pkg-config meson ninja-build \
    libdbus-1-dev libglib2.0-dev \
    ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /var/log/supervisor /app
WORKDIR /app

# Install Python deps first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir --upgrade pip \
 && if [ -s requirements.txt ]; then pip3 install --no-cache-dir -r requirements.txt; fi

# Ensure control API deps regardless of project requirements
RUN pip3 install --no-cache-dir fastapi "uvicorn[standard]" pydantic

# Copy application code
COPY . /app

# Copy runtime configs
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8080 5901

CMD ["/usr/local/bin/entrypoint.sh"]


