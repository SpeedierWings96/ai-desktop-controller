#!/usr/bin/env python3
"""
AI Desktop Controller - Quick Start Script
Simple script to get you up and running quickly
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def print_banner():
    """Print welcome banner"""
    print("\n" + "="*60)
    print("🤖  AI DESKTOP CONTROLLER - QUICK START")
    print("="*60)
    print("Real Linux desktop automation with OpenAI integration")
    print()

def check_requirements():
    """Check if basic requirements are met"""
    print("🔍 Checking requirements...")

    issues = []

    # Check Python version
    if sys.version_info < (3, 8):
        issues.append(f"Python 3.8+ required (found {sys.version_info.major}.{sys.version_info.minor})")

    # Check config file
    if not Path("config.json").exists():
        issues.append("config.json not found - run setup.py first")
    else:
        try:
            with open("config.json") as f:
                config = json.load(f)
                if not config.get("openai", {}).get("api_key"):
                    issues.append("OpenAI API key not configured in config.json")
        except Exception as e:
            issues.append(f"Error reading config.json: {e}")

    # Check core dependencies
    try:
        import openai
        import pyautogui
        import cv2
        import PIL
    except ImportError as e:
        issues.append(f"Missing Python dependencies: {e}")
        issues.append("Run: pip install -r requirements.txt")

    # Check display
    if not os.environ.get('DISPLAY'):
        issues.append("No DISPLAY environment variable - GUI may not work")

    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n💡 To fix these issues:")
        print("   1. Run: python3 setup.py")
        print("   2. Edit config.json to add your OpenAI API key")
        print("   3. Install missing dependencies")
        return False
    else:
        print("✅ All requirements met!")
        return True

def show_menu():
    """Show main menu options"""
    print("\n📋 What would you like to do?")
    print()
    print("1. 🌐 Start Web Interface (Recommended)")
    print("2. 🎯 Execute a Specific Task")
    print("3. 🧠 Start Autonomous Mode")
    print("4. 📸 Take Screenshot & Analyze")
    print("5. ⚙️  Run Setup")
    print("6. 📖 Show Help")
    print("7. 🚪 Exit")
    print()

def start_web_interface():
    """Start the web interface"""
    print("🌐 Starting web interface...")
    print("   • Dashboard will be available at: http://localhost:8080")
    print("   • Press Ctrl+C to stop the server")
    print()

    try:
        subprocess.run([sys.executable, "web_interface.py"])
    except KeyboardInterrupt:
        print("\n👋 Web interface stopped")
    except FileNotFoundError:
        print("❌ web_interface.py not found")
    except Exception as e:
        print(f"❌ Error starting web interface: {e}")

def execute_task():
    """Execute a specific task"""
    print("🎯 Task Execution Mode")
    print()
    print("Examples:")
    print("  • 'open firefox and go to google.com'")
    print("  • 'take a screenshot of the desktop'")
    print("  • 'open terminal and run ls command'")
    print("  • 'find and open the calculator app'")
    print()

    task = input("Enter your task: ").strip()
    if not task:
        print("❌ No task entered")
        return

    print(f"🚀 Executing task: {task}")
    print("   (This may take a few moments...)")

    try:
        subprocess.run([
            sys.executable,
            "ai_desktop_controller.py",
            "--task",
            task
        ])
    except FileNotFoundError:
        print("❌ ai_desktop_controller.py not found")
    except Exception as e:
        print(f"❌ Error executing task: {e}")

def start_autonomous():
    """Start autonomous mode"""
    print("🧠 Autonomous Mode")
    print()
    print("⚠️  WARNING: The AI will control your desktop independently!")
    print("   • Move mouse to top-left corner to emergency stop")
    print("   • Press Ctrl+C to stop autonomous mode")
    print("   • Monitor the AI's actions carefully")
    print()

    confirm = input("Start autonomous mode? (type 'yes' to confirm): ").lower().strip()
    if confirm != 'yes':
        print("❌ Autonomous mode cancelled")
        return

    print("🚀 Starting autonomous mode...")

    try:
        subprocess.run([sys.executable, "ai_desktop_controller.py", "--autonomous"])
    except KeyboardInterrupt:
        print("\n🛑 Autonomous mode stopped")
    except FileNotFoundError:
        print("❌ ai_desktop_controller.py not found")
    except Exception as e:
        print(f"❌ Error in autonomous mode: {e}")

def take_screenshot():
    """Take and analyze screenshot"""
    print("📸 Screenshot & Analysis")
    print("   Taking screenshot and analyzing with AI...")

    try:
        subprocess.run([sys.executable, "ai_desktop_controller.py", "--screenshot"])
    except FileNotFoundError:
        print("❌ ai_desktop_controller.py not found")
    except Exception as e:
        print(f"❌ Error taking screenshot: {e}")

def run_setup():
    """Run the setup script"""
    print("⚙️  Running setup...")

    try:
        subprocess.run([sys.executable, "setup.py"])
    except FileNotFoundError:
        print("❌ setup.py not found")
    except Exception as e:
        print(f"❌ Error running setup: {e}")

def show_help():
    """Show help information"""
    print("\n📖 AI Desktop Controller Help")
    print("="*40)
    print()
    print("🔧 Setup:")
    print("   1. Run setup.py to install dependencies")
    print("   2. Get OpenAI API key from https://platform.openai.com/")
    print("   3. Add API key to config.json")
    print()
    print("🎮 Usage Modes:")
    print("   • Web Interface: Best for beginners and monitoring")
    print("   • Task Execution: Give AI specific instructions")
    print("   • Autonomous: Let AI explore your desktop")
    print("   • Screenshot: Analyze current desktop state")
    print()
    print("🛡️  Safety:")
    print("   • Emergency stop: Move mouse to top-left corner")
    print("   • All actions are logged in logs/ directory")
    print("   • Rate limiting prevents excessive actions")
    print()
    print("📁 Important Files:")
    print("   • config.json - Configuration settings")
    print("   • logs/ - Activity logs")
    print("   • screenshots/ - AI screenshots")
    print()
    print("🆘 Troubleshooting:")
    print("   • Check logs/ for error details")
    print("   • Ensure DISPLAY environment variable is set")
    print("   • Verify OpenAI API key is valid")
    print()

def main():
    """Main program loop"""
    print_banner()

    # Check if we can run
    if not check_requirements():
        print("\n💡 Fix the issues above and try again.")
        sys.exit(1)

    # Main menu loop
    while True:
        show_menu()

        try:
            choice = input("Choose an option (1-7): ").strip()

            if choice == '1':
                start_web_interface()
            elif choice == '2':
                execute_task()
            elif choice == '3':
                start_autonomous()
            elif choice == '4':
                take_screenshot()
            elif choice == '5':
                run_setup()
            elif choice == '6':
                show_help()
            elif choice == '7':
                print("\n👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1-7.")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break

        # Pause before showing menu again
        if choice in ['1', '2', '3', '4', '5']:
            input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()