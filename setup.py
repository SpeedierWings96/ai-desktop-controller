#!/usr/bin/env python3
"""
AI Desktop Controller Setup Script
Installs dependencies, configures the system, and sets up the AI desktop controller.
"""

import os
import sys
import subprocess
import platform
import json
import shutil
from pathlib import Path
import pkg_resources
from typing import List, Dict, Optional

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(message: str, color: str = Colors.WHITE) -> None:
    """Print colored message to terminal"""
    print(f"{color}{message}{Colors.END}")

def print_header(title: str) -> None:
    """Print a formatted header"""
    print_colored("\n" + "="*60, Colors.CYAN)
    print_colored(f"  {title}", Colors.BOLD + Colors.WHITE)
    print_colored("="*60, Colors.CYAN)

def print_step(step: str) -> None:
    """Print a setup step"""
    print_colored(f"🔧 {step}", Colors.BLUE)

def print_success(message: str) -> None:
    """Print success message"""
    print_colored(f"✅ {message}", Colors.GREEN)

def print_warning(message: str) -> None:
    """Print warning message"""
    print_colored(f"⚠️  {message}", Colors.YELLOW)

def print_error(message: str) -> None:
    """Print error message"""
    print_colored(f"❌ {message}", Colors.RED)

class AIDesktopSetup:
    """Main setup class for AI Desktop Controller"""

    def __init__(self):
        self.python_version = sys.version_info
        self.platform = platform.system().lower()
        self.distro = self.get_linux_distro()
        self.requirements_file = Path("requirements.txt")
        self.config_file = Path("config.json")

        # Required directories
        self.directories = [
            "logs",
            "screenshots",
            "templates",
            "static"
        ]

        # System packages needed
        self.system_packages = {
            'ubuntu': ['python3-tk', 'python3-dev', 'wmctrl', 'xdotool', 'scrot', 'tesseract-ocr'],
            'debian': ['python3-tk', 'python3-dev', 'wmctrl', 'xdotool', 'scrot', 'tesseract-ocr'],
            'fedora': ['tkinter', 'python3-devel', 'wmctrl', 'xdotool', 'scrot', 'tesseract'],
            'centos': ['tkinter', 'python3-devel', 'wmctrl', 'xdotool', 'scrot', 'tesseract'],
            'arch': ['tk', 'python', 'wmctrl', 'xdotool', 'scrot', 'tesseract'],
            'opensuse': ['python3-tk', 'python3-devel', 'wmctrl', 'xdotool', 'scrot', 'tesseract-ocr']
        }

    def get_linux_distro(self) -> str:
        """Detect Linux distribution"""
        try:
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('ID='):
                        distro = line.split('=')[1].strip().strip('"')
                        return distro.lower()
        except:
            pass

        # Fallback detection methods
        if shutil.which('apt'):
            return 'ubuntu'
        elif shutil.which('yum') or shutil.which('dnf'):
            return 'fedora'
        elif shutil.which('pacman'):
            return 'arch'
        elif shutil.which('zypper'):
            return 'opensuse'
        else:
            return 'unknown'

    def check_system_requirements(self) -> bool:
        """Check if system meets requirements"""
        print_step("Checking system requirements...")

        success = True

        # Check Python version
        if self.python_version < (3, 8):
            print_error(f"Python 3.8+ required, found {self.python_version.major}.{self.python_version.minor}")
            success = False
        else:
            print_success(f"Python {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")

        # Check platform
        if self.platform != 'linux':
            print_error(f"Linux required, found {self.platform}")
            success = False
        else:
            print_success(f"Platform: {self.platform}")

        # Check if we have a display
        if not os.environ.get('DISPLAY'):
            print_warning("No DISPLAY environment variable found. GUI features may not work.")
        else:
            print_success(f"Display: {os.environ.get('DISPLAY')}")

        # Check for X11
        if not shutil.which('xrandr'):
            print_warning("xrandr not found. Some screen detection features may not work.")
        else:
            print_success("X11 tools available")

        return success

    def install_system_packages(self) -> bool:
        """Install required system packages"""
        print_step("Installing system packages...")

        if self.distro == 'unknown':
            print_warning("Unknown Linux distribution. Please install these packages manually:")
            print("  - python3-tk (or tkinter)")
            print("  - python3-dev")
            print("  - wmctrl")
            print("  - xdotool")
            print("  - scrot")
            print("  - tesseract-ocr")
            return True

        packages = self.system_packages.get(self.distro, [])
        if not packages:
            print_warning(f"No package list for {self.distro}. Manual installation may be required.")
            return True

        try:
            if self.distro in ['ubuntu', 'debian']:
                cmd = ['sudo', 'apt', 'update']
                subprocess.run(cmd, check=True, capture_output=True)
                cmd = ['sudo', 'apt', 'install', '-y'] + packages
            elif self.distro in ['fedora', 'centos']:
                package_manager = 'dnf' if shutil.which('dnf') else 'yum'
                cmd = ['sudo', package_manager, 'install', '-y'] + packages
            elif self.distro == 'arch':
                cmd = ['sudo', 'pacman', '-S', '--noconfirm'] + packages
            elif self.distro == 'opensuse':
                cmd = ['sudo', 'zypper', 'install', '-y'] + packages
            else:
                print_warning(f"Unsupported distribution: {self.distro}")
                return True

            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print_success("System packages installed successfully")
                return True
            else:
                print_error(f"Failed to install system packages: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print_error(f"Error installing system packages: {e}")
            return False
        except FileNotFoundError:
            print_error("Package manager not found. Please install packages manually.")
            return False

    def install_python_packages(self) -> bool:
        """Install Python packages from requirements.txt"""
        print_step("Installing Python packages...")

        if not self.requirements_file.exists():
            print_error(f"Requirements file not found: {self.requirements_file}")
            return False

        try:
            # Upgrade pip first
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'],
                         check=True, capture_output=True)

            # Install requirements
            cmd = [sys.executable, '-m', 'pip', 'install', '-r', str(self.requirements_file)]
            print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print_success("Python packages installed successfully")
                return True
            else:
                print_error(f"Failed to install Python packages: {result.stderr}")
                print("You can try installing manually with:")
                print(f"  pip install -r {self.requirements_file}")
                return False

        except subprocess.CalledProcessError as e:
            print_error(f"Error installing Python packages: {e}")
            return False

    def create_directories(self) -> bool:
        """Create necessary directories"""
        print_step("Creating directories...")

        try:
            for directory in self.directories:
                Path(directory).mkdir(exist_ok=True)
                print(f"  Created: {directory}")

            print_success("Directories created successfully")
            return True
        except Exception as e:
            print_error(f"Error creating directories: {e}")
            return False

    def setup_configuration(self) -> bool:
        """Set up configuration file"""
        print_step("Setting up configuration...")

        if self.config_file.exists():
            print_warning(f"Config file already exists: {self.config_file}")
            response = input("Do you want to overwrite it? (y/N): ").lower().strip()
            if response != 'y':
                print("Using existing configuration.")
                return True

        # Get OpenAI API key
        api_key = input(f"{Colors.YELLOW}Enter your OpenAI API key (or press Enter to skip): {Colors.END}").strip()

        config = {
            "openai": {
                "api_key": api_key,
                "model": "gpt-4-vision-preview",
                "max_tokens": 1000,
                "temperature": 0.1,
                "timeout": 30
            },
            "desktop": {
                "screenshot_quality": 85,
                "max_screenshot_size": [1920, 1080],
                "click_delay": 0.2,
                "type_delay": 0.05,
                "safety_mode": True,
                "failsafe_enabled": True,
                "screenshot_interval": 2.0
            },
            "ai": {
                "autonomous_mode": False,
                "decision_interval": 3.0,
                "max_thinking_time": 15.0,
                "confidence_threshold": 0.7,
                "max_iterations_per_task": 20,
                "exploration_probability": 0.3
            },
            "safety": {
                "max_actions_per_minute": 25,
                "restricted_areas": [
                    {"x": 0, "y": 0, "width": 50, "height": 50, "reason": "top-left failsafe corner"}
                ],
                "forbidden_applications": [
                    "sudo",
                    "rm",
                    "passwd",
                    "system-settings"
                ],
                "require_confirmation": [
                    "shutdown",
                    "reboot",
                    "delete",
                    "format"
                ]
            },
            "logging": {
                "level": "INFO",
                "max_log_files": 10,
                "screenshot_logging": True,
                "action_logging": True,
                "ai_response_logging": True
            },
            "interface": {
                "show_mouse_trail": True,
                "highlight_clicks": True,
                "show_ai_thinking": True,
                "voice_feedback": False,
                "web_interface_port": 8080
            },
            "experimental": {
                "ocr_enabled": True,
                "object_detection": False,
                "learning_mode": False,
                "memory_persistence": True
            }
        }

        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)

            print_success(f"Configuration saved to {self.config_file}")

            if not api_key:
                print_warning("No OpenAI API key provided.")
                print(f"Please edit {self.config_file} and add your API key to get started.")

            return True

        except Exception as e:
            print_error(f"Error creating configuration: {e}")
            return False

    def test_installation(self) -> bool:
        """Test if installation works"""
        print_step("Testing installation...")

        try:
            # Test importing required modules
            test_imports = [
                'openai',
                'pyautogui',
                'cv2',
                'PIL',
                'pynput',
                'psutil',
                'flask'
            ]

            failed_imports = []
            for module in test_imports:
                try:
                    __import__(module)
                    print(f"  ✓ {module}")
                except ImportError:
                    failed_imports.append(module)
                    print_error(f"  ✗ {module}")

            if failed_imports:
                print_error(f"Failed to import: {', '.join(failed_imports)}")
                print("Try running: pip install -r requirements.txt")
                return False

            # Test basic functionality
            try:
                import pyautogui
                screen_size = pyautogui.size()
                print_success(f"Screen detection working: {screen_size}")
            except Exception as e:
                print_warning(f"Screen detection issue: {e}")

            print_success("Installation test completed")
            return True

        except Exception as e:
            print_error(f"Error testing installation: {e}")
            return False

    def create_launcher_scripts(self) -> bool:
        """Create convenient launcher scripts"""
        print_step("Creating launcher scripts...")

        try:
            # Main launcher script
            launcher_script = \"\"\"#!/bin/bash
# AI Desktop Controller Launcher Script

echo "🤖 AI Desktop Controller"
echo "========================="

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "❌ config.json not found!"
    echo "Please run setup.py first or create the config file."
    exit 1
fi

# Check for OpenAI API key
if ! grep -q '"api_key": ""' config.json && grep -q '"api_key":' config.json; then
    echo "✅ Configuration found"
else
    echo "⚠️  Warning: OpenAI API key may not be configured"
    echo "   Edit config.json to add your API key"
fi

# Parse command line arguments
case "$1" in
    "web")
        echo "🌐 Starting web interface..."
        python3 web_interface.py --host 0.0.0.0 --port ${2:-8080}
        ;;
    "task")
        if [ -z "$2" ]; then
            echo "Usage: $0 task 'task description'"
            exit 1
        fi
        echo "🎯 Executing task: $2"
        python3 ai_desktop_controller.py --task "$2"
        ;;
    "auto")
        echo "🧠 Starting autonomous mode..."
        echo "   Press Ctrl+C to stop"
        python3 ai_desktop_controller.py --autonomous
        ;;
    "screenshot")
        echo "📸 Taking screenshot and analyzing..."
        python3 ai_desktop_controller.py --screenshot
        ;;
    *)
        echo "Usage:"
        echo "  $0 web [port]           - Start web interface (default port 8080)"
        echo "  $0 task 'description'   - Execute specific task"
        echo "  $0 auto                 - Start autonomous mode"
        echo "  $0 screenshot           - Take and analyze screenshot"
        echo ""
        echo "Examples:"
        echo "  $0 web 9000"
        echo "  $0 task 'open firefox and go to google.com'"
        echo "  $0 auto"
        ;;
esac
\"\"\"

            with open("launch.sh", "w") as f:
                f.write(launcher_script)
            os.chmod("launch.sh", 0o755)

            # Desktop entry for GUI
            desktop_entry = f\"\"\"[Desktop Entry]
Version=1.0
Type=Application
Name=AI Desktop Controller
Comment=AI-powered desktop automation and control
Exec={Path.cwd()}/launch.sh web
Icon=applications-system
Terminal=true
Categories=System;Utility;Development;
\"\"\"

            desktop_dir = Path.home() / ".local/share/applications"
            desktop_dir.mkdir(parents=True, exist_ok=True)

            with open(desktop_dir / "ai-desktop-controller.desktop", "w") as f:
                f.write(desktop_entry)

            print_success("Launcher scripts created:")
            print("  - ./launch.sh (command line)")
            print("  - Desktop entry (applications menu)")

            return True

        except Exception as e:
            print_error(f"Error creating launcher scripts: {e}")
            return False

    def print_final_instructions(self) -> None:
        \"\"\"Print final setup instructions\"\"\"
        print_header("🎉 Installation Complete!")

        print_colored("\\n📋 Next Steps:", Colors.BOLD)
        print_colored("1. Add your OpenAI API key to config.json", Colors.WHITE)
        print_colored("2. Run the AI Desktop Controller:", Colors.WHITE)
        print_colored("   • Web Interface:  ./launch.sh web", Colors.CYAN)
        print_colored("   • Execute Task:   ./launch.sh task 'open browser'", Colors.CYAN)
        print_colored("   • Autonomous:     ./launch.sh auto", Colors.CYAN)
        print_colored("   • Screenshot:     ./launch.sh screenshot", Colors.CYAN)

        print_colored("\\n🔧 Advanced Usage:", Colors.BOLD)
        print_colored("   python3 ai_desktop_controller.py --help", Colors.WHITE)
        print_colored("   python3 web_interface.py --help", Colors.WHITE)

        print_colored("\\n📁 Important Files:", Colors.BOLD)
        print_colored("   config.json       - Configuration", Colors.WHITE)
        print_colored("   logs/            - Activity logs", Colors.WHITE)
        print_colored("   screenshots/     - AI screenshots", Colors.WHITE)
        print_colored("   requirements.txt - Python dependencies", Colors.WHITE)

        print_colored("\\n⚠️  Safety Notes:", Colors.YELLOW)
        print_colored("   • Move mouse to top-left corner for emergency stop", Colors.WHITE)
        print_colored("   • AI actions are limited by safety settings", Colors.WHITE)
        print_colored("   • Review logs regularly for monitoring", Colors.WHITE)

        print_colored("\\n🆘 Troubleshooting:", Colors.BOLD)
        print_colored("   • Check logs/ directory for error details", Colors.WHITE)
        print_colored("   • Ensure DISPLAY environment variable is set", Colors.WHITE)
        print_colored("   • Verify OpenAI API key is valid", Colors.WHITE)
        print_colored("   • Run with --debug flag for verbose output", Colors.WHITE)

    def run_setup(self) -> bool:
        \"\"\"Run the complete setup process\"\"\"
        print_header("🤖 AI Desktop Controller Setup")
        print_colored("This will install and configure the AI Desktop Controller", Colors.WHITE)

        # Confirm setup
        if sys.stdin.isatty():  # Only ask if running interactively
            response = input(f"\\n{Colors.YELLOW}Continue with setup? (Y/n): {Colors.END}").lower().strip()
            if response and response != 'y' and response != 'yes':
                print("Setup cancelled.")
                return False

        success = True

        # Run setup steps
        steps = [
            ("System Requirements", self.check_system_requirements),
            ("System Packages", self.install_system_packages),
            ("Python Packages", self.install_python_packages),
            ("Directories", self.create_directories),
            ("Configuration", self.setup_configuration),
            ("Installation Test", self.test_installation),
            ("Launcher Scripts", self.create_launcher_scripts)
        ]

        for step_name, step_func in steps:
            print_header(f"Step: {step_name}")
            if not step_func():
                print_error(f"Setup step failed: {step_name}")
                success = False

                # Ask if user wants to continue
                if sys.stdin.isatty():
                    response = input(f"{Colors.YELLOW}Continue anyway? (y/N): {Colors.END}").lower().strip()
                    if response != 'y':
                        break

        if success:
            self.print_final_instructions()
        else:
            print_error("Setup completed with errors. Please review the output above.")

        return success

def main():
    \"\"\"Main entry point\"\"\"
    import argparse

    parser = argparse.ArgumentParser(description="AI Desktop Controller Setup")
    parser.add_argument("--no-system-packages", action="store_true",
                       help="Skip system package installation")
    parser.add_argument("--python-only", action="store_true",
                       help="Only install Python packages")
    parser.add_argument("--config-only", action="store_true",
                       help="Only setup configuration")
    args = parser.parse_args()

    setup = AIDesktopSetup()

    try:
        if args.config_only:
            print_header("🔧 Configuration Setup Only")
            return setup.setup_configuration()
        elif args.python_only:
            print_header("🐍 Python Packages Only")
            return setup.install_python_packages()
        else:
            # Skip system packages if requested
            if args.no_system_packages:
                setup.install_system_packages = lambda: True

            return setup.run_setup()

    except KeyboardInterrupt:
        print_colored("\\n\\n⚠️  Setup interrupted by user", Colors.YELLOW)
        return False
    except Exception as e:
        print_error(f"Setup failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)