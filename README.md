# 🤖 AI Desktop Controller

## Dockerized Linux Desktop with live noVNC view

This app can run inside a container that provides a full Linux desktop (XFCE) accessible via your browser using noVNC, and runs the Python controller app alongside the desktop session.

### Prerequisites
- Docker and Docker Compose

### Build
```bash
docker compose build
```

### Run
```bash
set VNC_PASSWORD=mysafepass  # Windows PowerShell: $env:VNC_PASSWORD="mysafepass"
docker compose up -d
```

Then open your browser to `http://localhost:8080` for the live desktop. Raw VNC is available on `localhost:5901`.

Environment variables:
- `VNC_PASSWORD` (default `changeme`)
- `RESOLUTION` (default `1920x1080`)
- `DEPTH` (default `24`)

The application code is mounted into `/app` in the container and started by Supervisor using `python3 run.py` (fallback to `ai_desktop_controller.py`). Modify `supervisord.conf` if you need a different startup.

### Control API
A FastAPI service runs at `http://localhost:8765` to control the desktop.

Examples (PowerShell):
```powershell
# Move mouse to x=400, y=300
Invoke-RestMethod -Method Post -Uri http://localhost:8765/move -Body (@{x=400;y=300} | ConvertTo-Json) -ContentType 'application/json'

# Click left button
Invoke-RestMethod -Method Post -Uri http://localhost:8765/click -Body (@{button=1} | ConvertTo-Json) -ContentType 'application/json'

# Type text
Invoke-RestMethod -Method Post -Uri http://localhost:8765/type -Body (@{text='hello from api'} | ConvertTo-Json) -ContentType 'application/json'

# Press a key (e.g., Super/Windows key)
Invoke-RestMethod -Method Post -Uri http://localhost:8765/key -Body (@{key='Super_L'} | ConvertTo-Json) -ContentType 'application/json'

# List windows
Invoke-RestMethod -Method Get -Uri http://localhost:8765/windows

# Activate a window by id
Invoke-RestMethod -Method Post -Uri http://localhost:8765/activate -Body (@{id='0x04000007'} | ConvertTo-Json) -ContentType 'application/json'

# Get a screenshot (PNG bytes)
Invoke-WebRequest -Uri http://localhost:8765/screenshot -OutFile screenshot.png
```

Notes:
- Keys use xdotool names (e.g., `Return`, `Super_L`, `Ctrl+Alt+t`). Use `xdotool key` chord notation for combos.
- Window IDs come from `wmctrl -lx` output returned by `/windows`.

### Stop and clean up
```bash
docker compose down
```

### Notes
- The container uses TigerVNC + noVNC to expose the Linux desktop.
- Use the VNC password you set with `VNC_PASSWORD` when prompted in noVNC.

**Real Linux Desktop Automation with OpenAI Integration**

An advanced AI-powered desktop controller that gives OpenAI's GPT-4 Vision the ability to see, understand, and control your actual Linux desktop environment. The AI can take screenshots, analyze what's on screen, click buttons, type text, open applications, and perform complex desktop tasks autonomously.

![AI Desktop Controller Demo](https://img.shields.io/badge/AI-Desktop%20Controller-blue?style=for-the-badge&logo=robot)
![Linux](https://img.shields.io/badge/Linux-Compatible-green?style=for-the-badge&logo=linux)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4%20Vision-orange?style=for-the-badge&logo=openai)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)

## 🌟 Features

### 🎯 Core AI Capabilities
- **Real Desktop Control**: Take actual screenshots and control your real Linux desktop
- **OpenAI GPT-4 Vision**: Advanced AI analysis of desktop screenshots
- **Autonomous Mode**: AI explores and interacts with your desktop independently  
- **Task Execution**: Give the AI high-level tasks like "open browser and search for cats"
- **Smart Interactions**: Context-aware clicking, typing, and navigation

### 🖥️ Desktop Automation
- **Screenshot Analysis**: AI sees and understands your desktop layout
- **Mouse Control**: Precise cursor movement and clicking
- **Keyboard Input**: Natural text typing and keyboard shortcuts
- **Window Management**: Open, close, and navigate applications
- **Multi-tasking**: Execute complex workflows across multiple applications

### 🌐 Web Interface
- **Real-time Dashboard**: Monitor AI activity with live screenshots
- **Task Management**: Queue and execute AI tasks remotely
- **Live Monitoring**: Watch the AI work in real-time
- **Configuration Panel**: Adjust AI settings and safety parameters
- **Activity Logging**: Complete audit trail of all AI actions

### 🛡️ Safety & Security
- **Failsafe System**: Emergency stop by moving mouse to corner
- **Rate Limiting**: Prevents excessive actions per minute
- **Restricted Areas**: Define no-go zones on the desktop
- **Action Confirmation**: Require approval for sensitive operations
- **Audit Logging**: Complete logs of all AI activities

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/SpeedierWings96/ai-desktop-controller.git
cd ai-desktop-controller

# Run the automated setup
python3 setup.py
```

### 2. Configure OpenAI API Key
Edit `config.json` and add your API key:
```json
{
  "openai": {
    "api_key": "sk-your-api-key-here",
    "model": "gpt-4-vision-preview"
  }
}
```

### 3. Launch the AI Controller

**Quick Start Menu**:
```bash
python3 run.py
```

**Web Interface (Recommended)**:
```bash
python3 web_interface.py
```
Then open http://localhost:8080 in your browser.

**Command Line**:
```bash
# Execute a specific task
python3 ai_desktop_controller.py --task "open firefox and go to google.com"

# Start autonomous mode
python3 ai_desktop_controller.py --autonomous

# Take and analyze screenshot
python3 ai_desktop_controller.py --screenshot
```

## 💻 Usage Examples

### Basic Task Execution
```bash
# Open applications
python3 ai_desktop_controller.py --task "open the terminal"

# Web browsing
python3 ai_desktop_controller.py --task "search google for python tutorials"

# File operations
python3 ai_desktop_controller.py --task "open the file manager"
```

### Autonomous Mode
```bash
# Let AI explore your desktop independently
python3 ai_desktop_controller.py --autonomous

# The AI will:
# - Analyze the current desktop
# - Find interesting applications to open
# - Interact with UI elements
# - Navigate between windows
# - Take screenshots of its progress
```

## 🛡️ Safety Features

### Emergency Stop
- **Mouse Failsafe**: Move mouse to top-left corner (0,0) to immediately stop AI
- **Keyboard Interrupt**: Press Ctrl+C in terminal to stop
- **Web Interface**: Click "Emergency Stop" button

### Best Practices
1. **Start with Simple Tasks**: Test with basic operations first
2. **Monitor Initially**: Watch the AI's first few operations closely
3. **Use Sandbox Environment**: Test in a virtual machine first
4. **Backup Important Data**: Ensure your data is backed up

## 📋 Requirements

- **OS**: Linux (Ubuntu, Debian, Fedora, CentOS, Arch, openSUSE)
- **Python**: 3.8 or higher
- **Desktop Environment**: X11 (Wayland support experimental)
- **OpenAI API Key**: GPT-4 Vision access required

### System Packages
```bash
# Ubuntu/Debian
sudo apt install python3-tk python3-dev wmctrl xdotool scrot tesseract-ocr

# Fedora/CentOS
sudo dnf install tkinter python3-devel wmctrl xdotool scrot tesseract

# Arch Linux
sudo pacman -S tk python wmctrl xdotool scrot tesseract
```

## 🔧 Configuration

The `config.json` file controls AI behavior, safety settings, and performance parameters. Key sections include:

- **OpenAI Settings**: API key, model, and parameters
- **Desktop Control**: Screenshot quality, delays, safety mode
- **AI Behavior**: Autonomous mode, decision intervals, confidence thresholds
- **Safety Settings**: Rate limits, forbidden apps, restricted areas

## 🌐 Web Interface

Access the web dashboard at http://localhost:8080 for:

- **Live Screenshots**: Real-time desktop monitoring
- **Task Execution**: Submit tasks through web interface
- **Activity Logs**: Complete history of AI actions
- **System Metrics**: CPU, memory, and performance monitoring
- **Emergency Controls**: Immediate AI shutdown capabilities

## 📊 Monitoring & Logging

- **Activity Logs**: `logs/ai_desktop_YYYYMMDD_HHMMSS.log`
- **Screenshots**: `screenshots/screen_YYYYMMDD_HHMMSS.png`
- **Real-time Monitoring**: Web interface and command line tools

## 🐛 Troubleshooting

### Common Issues
- **API Key Issues**: Verify OpenAI API key in `config.json`
- **Screenshot Problems**: Check DISPLAY environment variable
- **Permission Errors**: Ensure proper file permissions
- **Dependency Issues**: Run `pip install -r requirements.txt`

### Debug Mode
```bash
python3 ai_desktop_controller.py --task "test task" --debug
```

## 🤝 Contributing

We welcome contributions! Areas where you can help:

- **Wayland Support**: Add support for Wayland desktop environments
- **OCR Integration**: Improve text recognition capabilities  
- **Voice Control**: Add speech recognition features
- **Documentation**: Improve guides and tutorials
- **Testing**: Add unit tests and integration tests

## ⚠️ Important Disclaimer

**This software gives AI control over your real desktop environment.** While comprehensive safety measures are in place, use at your own risk. The AI can:

- Click on any visible screen element
- Type text into any application  
- Open and close programs
- Navigate your file system

**Recommendations**: Test in a virtual machine first, backup important data, monitor AI activity closely, and start with simple tasks.

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **OpenAI**: For the GPT-4 Vision API
- **PyAutoGUI**: For desktop automation capabilities
- **OpenCV**: For computer vision processing
- **Flask**: For the web interface framework
- **Linux Community**: For open desktop environments

---

**🤖 Ready to give AI control of your desktop?**

*Built with ❤️ for AI researchers, automation enthusiasts, and the curious.*