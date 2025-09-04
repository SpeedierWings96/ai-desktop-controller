#!/usr/bin/env python3
"""
AI Desktop Controller - Real Linux Desktop Control with OpenAI Integration
Allows AI to take screenshots, analyze desktop, and perform real actions.
"""

import os
import sys
import time
import json
import base64
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import threading
import queue

# External dependencies
try:
    import openai
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    import pynput
    from pynput import mouse, keyboard
    import psutil
    import subprocess
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Install with: pip install openai pyautogui opencv-python pillow pynput psutil")
    sys.exit(1)

@dataclass
class DesktopAction:
    """Represents an action to be performed on the desktop"""
    action_type: str  # click, type, scroll, key_press, move, screenshot, analyze
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""

@dataclass
class ScreenElement:
    """Represents an element detected on screen"""
    type: str
    bounds: Tuple[int, int, int, int]  # x, y, width, height
    text: str = ""
    confidence: float = 0.0

class AIDesktopController:
    """Main AI Desktop Controller class"""

    def __init__(self, config_path: str = "config.json"):
        """Initialize the AI Desktop Controller"""
        self.config_path = config_path
        self.config = self.load_config()
        self.setup_logging()
        self.setup_openai()
        self.setup_automation()

        # State management
        self.is_running = False
        self.current_screenshot = None
        self.last_screenshot_time = 0
        self.action_queue = queue.Queue()
        self.screen_history = []
        self.interaction_count = 0

        # Safety limits
        self.max_actions_per_minute = 30
        self.action_timestamps = []
        self.screenshot_interval = 2.0  # seconds

        # Desktop state
        self.screen_size = pyautogui.size()
        self.current_mouse_pos = pyautogui.position()

        self.logger.info("AI Desktop Controller initialized")
        self.logger.info(f"Screen resolution: {self.screen_size}")

    def load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "openai": {
                "api_key": "",
                "model": "gpt-4-vision-preview",
                "max_tokens": 1000,
                "temperature": 0.1
            },
            "desktop": {
                "screenshot_quality": 85,
                "max_screenshot_size": [1920, 1080],
                "click_delay": 0.1,
                "type_delay": 0.05,
                "safety_mode": True
            },
            "ai": {
                "autonomous_mode": False,
                "decision_interval": 3.0,
                "max_thinking_time": 10.0,
                "confidence_threshold": 0.7
            }
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    for section, values in user_config.items():
                        if section in default_config:
                            default_config[section].update(values)
                        else:
                            default_config[section] = values
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            # Create default config file
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config file: {self.config_path}")
            print("Please add your OpenAI API key to the config file!")

        return default_config

    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_filename = f"ai_desktop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = log_dir / log_filename

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_openai(self):
        """Setup OpenAI client"""
        api_key = self.config["openai"]["api_key"]
        if not api_key:
            self.logger.error("OpenAI API key not found in config!")
            print("\n🔑 Please add your OpenAI API key to config.json:")
            print('   "openai": { "api_key": "sk-your-key-here" }')
            sys.exit(1)

        openai.api_key = api_key
        self.openai_client = openai

        # Test connection
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            self.logger.info("✅ OpenAI connection successful")
        except Exception as e:
            self.logger.error(f"❌ OpenAI connection failed: {e}")
            sys.exit(1)

    def setup_automation(self):
        """Setup desktop automation tools"""
        # Configure pyautogui
        pyautogui.PAUSE = self.config["desktop"]["click_delay"]
        pyautogui.FAILSAFE = True  # Move mouse to corner to stop

        # Disable fail-safe for headless environments if needed
        if self.config["desktop"]["safety_mode"]:
            self.logger.info("🛡️ Safety mode enabled - move mouse to top-left corner to emergency stop")
        else:
            pyautogui.FAILSAFE = False

    def take_screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """Take a screenshot of the desktop"""
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()

            # Resize if too large
            max_size = tuple(self.config["desktop"]["max_screenshot_size"])
            if screenshot.size[0] > max_size[0] or screenshot.size[1] > max_size[1]:
                screenshot.thumbnail(max_size, Image.Resampling.LANCZOS)

            self.current_screenshot = screenshot
            self.last_screenshot_time = time.time()

            # Save screenshot with timestamp
            screenshot_dir = Path("screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            screenshot_path = screenshot_dir / f"screen_{timestamp}.png"
            screenshot.save(screenshot_path)

            self.logger.info(f"Screenshot taken: {screenshot.size}")
            return screenshot

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            raise

    def encode_image_for_openai(self, image: Image.Image) -> str:
        """Encode image for OpenAI API"""
        from io import BytesIO

        buffer = BytesIO()
        image.save(buffer, format="PNG", quality=self.config["desktop"]["screenshot_quality"])
        image_data = buffer.getvalue()
        return base64.b64encode(image_data).decode('utf-8')

    def analyze_screen_with_ai(self, task: str = "analyze", additional_context: str = "") -> Dict[str, Any]:
        """Analyze current screen using OpenAI Vision"""
        if not self.current_screenshot:
            self.take_screenshot()

        image_base64 = self.encode_image_for_openai(self.current_screenshot)

        system_prompt = """You are an AI assistant that can see and control a Linux desktop. You can:
        1. Click on buttons, icons, menus, and UI elements
        2. Type text into input fields
        3. Navigate applications and windows
        4. Scroll through content
        5. Press keyboard shortcuts

        When analyzing the screen, provide:
        - What you can see on the desktop
        - Identify interactive elements (buttons, text fields, menus, etc.)
        - Suggest the next logical action based on the task
        - Provide exact coordinates for any actions

        Respond in JSON format with this structure:
        {
            "analysis": "Description of what you see",
            "elements": [{"type": "button/textfield/icon/etc", "text": "label", "x": 100, "y": 200, "confidence": 0.9}],
            "suggested_action": {
                "type": "click/type/key_press/scroll",
                "x": 100,
                "y": 200,
                "text": "text to type (if applicable)",
                "key": "key to press (if applicable)",
                "reasoning": "Why this action makes sense"
            }
        }"""

        user_prompt = f"""Current task: {task}

        {additional_context}

        Please analyze this Linux desktop screenshot and suggest the next action to take.

        Current mouse position: {self.current_mouse_pos}
        Screen resolution: {self.screen_size}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        Be precise with coordinates and confident in your suggestions."""

        try:
            response = openai.ChatCompletion.create(
                model=self.config["openai"]["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.config["openai"]["max_tokens"],
                temperature=self.config["openai"]["temperature"]
            )

            ai_response = response.choices[0].message.content
            self.logger.info(f"AI Analysis: {ai_response}")

            # Try to parse JSON response
            try:
                analysis = json.loads(ai_response)
                return analysis
            except json.JSONDecodeError:
                # Fallback if AI doesn't return proper JSON
                return {
                    "analysis": ai_response,
                    "elements": [],
                    "suggested_action": {
                        "type": "wait",
                        "reasoning": "Could not parse AI response as JSON"
                    }
                }

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            return {
                "analysis": f"Error during AI analysis: {e}",
                "elements": [],
                "suggested_action": {"type": "wait", "reasoning": "AI analysis failed"}
            }

    def execute_action(self, action: DesktopAction) -> bool:
        """Execute a desktop action"""
        if not self.check_rate_limit():
            self.logger.warning("Rate limit exceeded, skipping action")
            return False

        try:
            self.logger.info(f"Executing action: {action.action_type}")

            if action.action_type == "click":
                if action.x is not None and action.y is not None:
                    pyautogui.click(action.x, action.y)
                    self.current_mouse_pos = (action.x, action.y)
                    self.logger.info(f"Clicked at ({action.x}, {action.y})")

            elif action.action_type == "type":
                if action.text:
                    pyautogui.write(action.text, interval=self.config["desktop"]["type_delay"])
                    self.logger.info(f"Typed: {action.text}")

            elif action.action_type == "key_press":
                if action.key:
                    pyautogui.press(action.key)
                    self.logger.info(f"Pressed key: {action.key}")

            elif action.action_type == "scroll":
                if action.x is not None and action.y is not None:
                    pyautogui.scroll(action.y, x=action.x)
                    self.logger.info(f"Scrolled {action.y} at ({action.x}, {action.y})")

            elif action.action_type == "move":
                if action.x is not None and action.y is not None:
                    pyautogui.moveTo(action.x, action.y)
                    self.current_mouse_pos = (action.x, action.y)
                    self.logger.info(f"Moved to ({action.x}, {action.y})")

            elif action.action_type == "screenshot":
                self.take_screenshot()

            elif action.action_type == "wait":
                wait_time = action.x if action.x else 1
                time.sleep(wait_time)
                self.logger.info(f"Waited {wait_time} seconds")

            else:
                self.logger.warning(f"Unknown action type: {action.action_type}")
                return False

            self.interaction_count += 1
            self.action_timestamps.append(time.time())

            # Small delay after each action
            time.sleep(0.1)

            return True

        except Exception as e:
            self.logger.error(f"Failed to execute action {action.action_type}: {e}")
            return False

    def check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        current_time = time.time()
        # Remove timestamps older than 1 minute
        self.action_timestamps = [t for t in self.action_timestamps if current_time - t < 60]

        return len(self.action_timestamps) < self.max_actions_per_minute

    def get_active_windows(self) -> List[Dict]:
        """Get list of active windows"""
        try:
            result = subprocess.run(['wmctrl', '-l'], capture_output=True, text=True)
            windows = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        windows.append({
                            'id': parts[0],
                            'desktop': parts[1],
                            'host': parts[2],
                            'title': parts[3]
                        })
            return windows
        except Exception as e:
            self.logger.error(f"Failed to get active windows: {e}")
            return []

    def execute_ai_task(self, task: str, max_iterations: int = 10) -> bool:
        """Execute a high-level task using AI"""
        self.logger.info(f"🤖 Starting AI task: {task}")

        iteration = 0
        task_completed = False

        while iteration < max_iterations and not task_completed:
            iteration += 1
            self.logger.info(f"Task iteration {iteration}/{max_iterations}")

            # Take screenshot and analyze
            self.take_screenshot()
            analysis = self.analyze_screen_with_ai(task)

            # Log the analysis
            self.logger.info(f"AI sees: {analysis.get('analysis', 'No analysis')}")

            # Get suggested action
            suggested = analysis.get('suggested_action', {})
            if not suggested or suggested.get('type') == 'wait':
                self.logger.info("AI suggests waiting or no action needed")
                time.sleep(2)
                continue

            # Create and execute action
            action = DesktopAction(
                action_type=suggested.get('type', 'wait'),
                x=suggested.get('x'),
                y=suggested.get('y'),
                text=suggested.get('text'),
                key=suggested.get('key'),
                reasoning=suggested.get('reasoning', '')
            )

            self.logger.info(f"AI reasoning: {action.reasoning}")

            if action.action_type == 'task_complete':
                self.logger.info("🎉 AI reports task completed!")
                task_completed = True
                break

            # Execute the action
            success = self.execute_action(action)
            if not success:
                self.logger.warning("Action execution failed")

            # Wait before next iteration
            time.sleep(self.config["ai"]["decision_interval"])

        if task_completed:
            self.logger.info(f"✅ Task '{task}' completed successfully")
            return True
        else:
            self.logger.warning(f"⚠️ Task '{task}' reached max iterations without completion")
            return False

    def start_autonomous_mode(self):
        """Start autonomous AI desktop exploration"""
        self.logger.info("🧠 Starting autonomous mode")
        self.is_running = True

        try:
            while self.is_running:
                # Take screenshot and analyze current state
                self.take_screenshot()
                analysis = self.analyze_screen_with_ai(
                    task="explore and interact with the desktop",
                    additional_context="You are in autonomous exploration mode. Look for interesting applications to open, websites to browse, or tasks to perform."
                )

                # Get and execute suggested action
                suggested = analysis.get('suggested_action', {})
                if suggested and suggested.get('type') != 'wait':
                    action = DesktopAction(
                        action_type=suggested.get('type', 'wait'),
                        x=suggested.get('x'),
                        y=suggested.get('y'),
                        text=suggested.get('text'),
                        key=suggested.get('key'),
                        reasoning=suggested.get('reasoning', '')
                    )

                    self.execute_action(action)

                # Wait before next decision
                time.sleep(self.config["ai"]["decision_interval"])

        except KeyboardInterrupt:
            self.logger.info("Autonomous mode stopped by user")
        except Exception as e:
            self.logger.error(f"Error in autonomous mode: {e}")
        finally:
            self.is_running = False

    def stop(self):
        """Stop the AI controller"""
        self.is_running = False
        self.logger.info("🛑 AI Desktop Controller stopped")

    def get_system_info(self) -> Dict:
        """Get system information"""
        return {
            "screen_size": self.screen_size,
            "mouse_position": pyautogui.position(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "active_windows": self.get_active_windows(),
            "interactions_count": self.interaction_count
        }

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="AI Desktop Controller")
    parser.add_argument("--task", help="Specific task for AI to execute")
    parser.add_argument("--autonomous", action="store_true", help="Start autonomous mode")
    parser.add_argument("--screenshot", action="store_true", help="Take a screenshot and analyze")
    parser.add_argument("--config", default="config.json", help="Config file path")

    args = parser.parse_args()

    try:
        controller = AIDesktopController(args.config)

        if args.screenshot:
            controller.take_screenshot()
            analysis = controller.analyze_screen_with_ai()
            print(json.dumps(analysis, indent=2))

        elif args.task:
            controller.execute_ai_task(args.task)

        elif args.autonomous:
            print("🤖 Starting autonomous mode - Press Ctrl+C to stop")
            controller.start_autonomous_mode()

        else:
            print("🤖 AI Desktop Controller Ready")
            print("Available commands:")
            print("  --task 'description'  - Execute a specific task")
            print("  --autonomous          - Start autonomous exploration")
            print("  --screenshot          - Take and analyze screenshot")
            print("\nSystem Info:")
            info = controller.get_system_info()
            for key, value in info.items():
                print(f"  {key}: {value}")

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()