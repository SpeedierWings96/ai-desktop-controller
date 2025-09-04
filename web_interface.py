#!/usr/bin/env python3
"""
Web Interface for AI Desktop Controller
Provides a web-based control panel for monitoring and controlling the AI desktop automation
"""

import os
import sys
import json
import time
import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS
import logging

# Import our AI controller
try:
    from ai_desktop_controller import AIDesktopController, DesktopAction
except ImportError:
    print("Could not import ai_desktop_controller. Make sure it's in the same directory.")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ai-desktop-controller-secret-key-2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
ai_controller: Optional[AIDesktopController] = None
controller_thread: Optional[threading.Thread] = None
is_running = False
clients = set()

# Setup logging for web interface
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get current AI controller status"""
    global ai_controller

    if not ai_controller:
        return jsonify({
            'status': 'disconnected',
            'error': 'AI Controller not initialized'
        })

    try:
        system_info = ai_controller.get_system_info()
        return jsonify({
            'status': 'connected',
            'is_running': is_running,
            'autonomous_mode': ai_controller.config["ai"]["autonomous_mode"],
            'system_info': system_info,
            'interaction_count': ai_controller.interaction_count,
            'last_screenshot_time': ai_controller.last_screenshot_time,
            'config': ai_controller.config
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })

@app.route('/api/screenshot')
def get_screenshot():
    """Get latest screenshot as base64"""
    global ai_controller

    if not ai_controller:
        return jsonify({'error': 'AI Controller not initialized'})

    try:
        # Take new screenshot
        screenshot = ai_controller.take_screenshot()

        # Convert to base64
        import io
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return jsonify({
            'image': f'data:image/png;base64,{img_str}',
            'timestamp': time.time(),
            'size': screenshot.size
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/task', methods=['POST'])
def execute_task():
    """Execute a specific task"""
    global ai_controller

    if not ai_controller:
        return jsonify({'error': 'AI Controller not initialized'})

    data = request.get_json()
    task = data.get('task', '')

    if not task:
        return jsonify({'error': 'No task specified'})

    try:
        # Execute task in background thread
        def run_task():
            result = ai_controller.execute_ai_task(task)
            socketio.emit('task_completed', {
                'task': task,
                'success': result,
                'timestamp': datetime.now().isoformat()
            })

        task_thread = threading.Thread(target=run_task)
        task_thread.daemon = True
        task_thread.start()

        return jsonify({
            'status': 'started',
            'task': task,
            'message': 'Task execution started in background'
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/autonomous', methods=['POST'])
def toggle_autonomous():
    """Start/stop autonomous mode"""
    global ai_controller, controller_thread, is_running

    if not ai_controller:
        return jsonify({'error': 'AI Controller not initialized'})

    data = request.get_json()
    enable = data.get('enable', False)

    try:
        if enable and not is_running:
            # Start autonomous mode
            is_running = True
            ai_controller.is_running = True

            def autonomous_worker():
                try:
                    ai_controller.start_autonomous_mode()
                except Exception as e:
                    logger.error(f"Autonomous mode error: {e}")
                    socketio.emit('error', {'message': str(e)})
                finally:
                    global is_running
                    is_running = False

            controller_thread = threading.Thread(target=autonomous_worker)
            controller_thread.daemon = True
            controller_thread.start()

            return jsonify({
                'status': 'started',
                'autonomous_mode': True
            })

        elif not enable and is_running:
            # Stop autonomous mode
            is_running = False
            if ai_controller:
                ai_controller.stop()

            return jsonify({
                'status': 'stopped',
                'autonomous_mode': False
            })

        return jsonify({
            'status': 'no_change',
            'autonomous_mode': is_running
        })

    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update configuration"""
    global ai_controller

    if request.method == 'GET':
        if ai_controller:
            return jsonify(ai_controller.config)
        else:
            return jsonify({'error': 'AI Controller not initialized'})

    elif request.method == 'POST':
        if not ai_controller:
            return jsonify({'error': 'AI Controller not initialized'})

        try:
            new_config = request.get_json()

            # Update config
            ai_controller.config.update(new_config)

            # Save to file
            with open(ai_controller.config_path, 'w') as f:
                json.dump(ai_controller.config, f, indent=2)

            return jsonify({
                'status': 'updated',
                'config': ai_controller.config
            })
        except Exception as e:
            return jsonify({'error': str(e)})

@app.route('/api/action', methods=['POST'])
def execute_action():
    """Execute a single desktop action"""
    global ai_controller

    if not ai_controller:
        return jsonify({'error': 'AI Controller not initialized'})

    data = request.get_json()

    try:
        action = DesktopAction(
            action_type=data.get('type', 'wait'),
            x=data.get('x'),
            y=data.get('y'),
            text=data.get('text'),
            key=data.get('key'),
            reasoning=data.get('reasoning', 'Manual web interface action')
        )

        success = ai_controller.execute_action(action)

        return jsonify({
            'success': success,
            'action': {
                'type': action.action_type,
                'x': action.x,
                'y': action.y,
                'text': action.text,
                'key': action.key
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def analyze_screen():
    """Analyze current screen with AI"""
    global ai_controller

    if not ai_controller:
        return jsonify({'error': 'AI Controller not initialized'})

    data = request.get_json()
    task = data.get('task', 'analyze the current screen')
    context = data.get('context', '')

    try:
        analysis = ai_controller.analyze_screen_with_ai(task, context)
        return jsonify({
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/logs')
def view_logs():
    """View log files"""
    log_dir = Path('logs')
    if not log_dir.exists():
        return jsonify({'logs': []})

    log_files = []
    for log_file in log_dir.glob('*.log'):
        log_files.append({
            'name': log_file.name,
            'size': log_file.stat().st_size,
            'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
        })

    return jsonify({'logs': sorted(log_files, key=lambda x: x['modified'], reverse=True)})

@app.route('/logs/<filename>')
def get_log_file(filename):
    """Get specific log file"""
    log_dir = Path('logs')
    return send_from_directory(log_dir, filename)

# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    clients.add(request.sid)
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to AI Desktop Controller'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    clients.discard(request.sid)
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('request_screenshot')
def handle_screenshot_request():
    """Handle screenshot request via websocket"""
    global ai_controller

    if not ai_controller:
        emit('error', {'message': 'AI Controller not initialized'})
        return

    try:
        screenshot = ai_controller.take_screenshot()

        # Convert to base64
        import io
        buffer = io.BytesIO()
        screenshot.save(buffer, format='PNG', quality=70)  # Lower quality for faster transfer
        img_str = base64.b64encode(buffer.getvalue()).decode()

        emit('screenshot', {
            'image': f'data:image/png;base64,{img_str}',
            'timestamp': time.time(),
            'size': screenshot.size
        })
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('live_mode')
def handle_live_mode(data):
    """Handle live screenshot streaming"""
    enabled = data.get('enabled', False)
    interval = data.get('interval', 2)  # seconds

    if enabled:
        def live_stream():
            while enabled and request.sid in clients:
                try:
                    handle_screenshot_request()
                    socketio.sleep(interval)
                except:
                    break

        socketio.start_background_task(live_stream)

# Create templates directory and basic HTML
def create_templates():
    """Create template files if they don't exist"""
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)

    dashboard_html = \"\"\"
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>AI Desktop Controller</title>
    <script src=\"https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js\"></script>
    <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; }
        .header h1 { font-size: 28px; margin-bottom: 5px; }
        .header p { opacity: 0.9; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .dashboard { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { margin-bottom: 15px; color: #333; }
        .status { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-dot.connected { background: #4CAF50; animation: pulse 2s infinite; }
        .status-dot.disconnected { background: #f44336; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .controls { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 15px 0; }
        .btn { padding: 12px 16px; border: none; border-radius: 8px; cursor: pointer; font-weight: 500; transition: all 0.3s; }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a6fd8; transform: translateY(-1px); }
        .btn-secondary { background: #f8f9fa; color: #495057; border: 1px solid #dee2e6; }
        .btn-secondary:hover { background: #e9ecef; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .screenshot-area { text-align: center; border: 2px dashed #ddd; border-radius: 8px; padding: 20px; margin: 15px 0; }
        .screenshot-area img { max-width: 100%; max-height: 300px; border-radius: 4px; }
        .log-area { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 8px; height: 300px; overflow-y: auto; font-family: monospace; font-size: 12px; }
        .input-group { display: flex; gap: 10px; margin: 10px 0; }
        .input-group input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }
        .metric { text-align: center; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .metric-value { font-size: 24px; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 12px; color: #666; margin-top: 5px; }
        .full-width { grid-column: 1 / -1; }
        .two-column { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>🤖 AI Desktop Controller</h1>
        <p>Real-time AI desktop automation and control</p>
    </div>

    <div class=\"container\">
        <!-- Status and Metrics -->
        <div class=\"metrics\">
            <div class=\"metric\">
                <div class=\"metric-value\" id=\"status-value\">--</div>
                <div class=\"metric-label\">Status</div>
            </div>
            <div class=\"metric\">
                <div class=\"metric-value\" id=\"actions-count\">0</div>
                <div class=\"metric-label\">Actions Taken</div>
            </div>
            <div class=\"metric\">
                <div class=\"metric-value\" id=\"uptime\">00:00:00</div>
                <div class=\"metric-label\">Uptime</div>
            </div>
            <div class=\"metric\">
                <div class=\"metric-value\" id=\"cpu-usage\">--%</div>
                <div class=\"metric-label\">CPU Usage</div>
            </div>
        </div>

        <!-- Main Dashboard -->
        <div class=\"dashboard\">
            <!-- Controls -->
            <div class=\"card\">
                <h3>🎮 AI Controls</h3>
                <div class=\"status\">
                    <div class=\"status-dot disconnected\" id=\"connection-status\"></div>
                    <span id=\"status-text\">Disconnected</span>
                </div>

                <div class=\"controls\">
                    <button class=\"btn btn-primary\" onclick=\"takeScreenshot()\">📸 Screenshot</button>
                    <button class=\"btn btn-primary\" onclick=\"toggleAutonomous()\">🧠 Auto Mode</button>
                    <button class=\"btn btn-secondary\" onclick=\"analyzeScreen()\">🔍 Analyze</button>
                    <button class=\"btn btn-danger\" onclick=\"emergencyStop()\">🛑 Stop</button>
                </div>

                <div class=\"input-group\">
                    <input type=\"text\" id=\"task-input\" placeholder=\"Enter AI task...\" />
                    <button class=\"btn btn-primary\" onclick=\"executeTask()\">Execute</button>
                </div>

                <div class=\"input-group\">
                    <input type=\"number\" id=\"click-x\" placeholder=\"X\" />
                    <input type=\"number\" id=\"click-y\" placeholder=\"Y\" />
                    <button class=\"btn btn-secondary\" onclick=\"clickAt()\">Click</button>
                </div>
            </div>

            <!-- Screenshot Area -->
            <div class=\"card\">
                <h3>👁️ AI Vision</h3>
                <div class=\"screenshot-area\" id=\"screenshot-area\">
                    <p>No screenshot available</p>
                    <button class=\"btn btn-secondary\" onclick=\"requestScreenshot()\">Take Screenshot</button>
                </div>
                <div class=\"controls\">
                    <button class=\"btn btn-secondary\" onclick=\"toggleLiveMode()\">📹 Live Mode</button>
                    <button class=\"btn btn-secondary\" onclick=\"refreshScreenshot()\">🔄 Refresh</button>
                </div>
            </div>
        </div>

        <!-- Activity Log -->
        <div class=\"card full-width\">
            <h3>📋 Activity Log</h3>
            <div class=\"log-area\" id=\"activity-log\">
                <div>AI Desktop Controller Web Interface loaded...</div>
            </div>
            <div style=\"margin-top: 10px;\">
                <button class=\"btn btn-secondary\" onclick=\"clearLog()\">Clear Log</button>
                <button class=\"btn btn-secondary\" onclick=\"exportLog()\">Export Log</button>
            </div>
        </div>
    </div>

    <script>
        // Socket.IO connection
        const socket = io();
        let isLiveMode = false;
        let startTime = Date.now();

        // DOM elements
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('status-text');
        const activityLog = document.getElementById('activity-log');
        const screenshotArea = document.getElementById('screenshot-area');

        // Socket event handlers
        socket.on('connect', () => {
            updateConnectionStatus(true);
            log('Connected to AI Desktop Controller', 'success');
            refreshStatus();
        });

        socket.on('disconnect', () => {
            updateConnectionStatus(false);
            log('Disconnected from AI Desktop Controller', 'error');
        });

        socket.on('screenshot', (data) => {
            displayScreenshot(data.image, data.timestamp, data.size);
        });

        socket.on('task_completed', (data) => {
            log(`Task completed: ${data.task} (Success: ${data.success})`, data.success ? 'success' : 'error');
        });

        socket.on('error', (data) => {
            log(`Error: ${data.message}`, 'error');
        });

        // Utility functions
        function updateConnectionStatus(connected) {
            if (connected) {
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected';
                document.getElementById('status-value').textContent = 'Online';
            } else {
                statusDot.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected';
                document.getElementById('status-value').textContent = 'Offline';
            }
        }

        function log(message, type = 'info') {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.style.color = type === 'success' ? '#2ecc71' : type === 'error' ? '#e74c3c' : '#3498db';
            logEntry.innerHTML = `[${timestamp}] ${message}`;
            activityLog.appendChild(logEntry);
            activityLog.scrollTop = activityLog.scrollHeight;
        }

        function displayScreenshot(imageData, timestamp, size) {
            screenshotArea.innerHTML = `
                <img src=\"${imageData}\" alt=\"Desktop Screenshot\" />
                <p>Screenshot taken at ${new Date(timestamp * 1000).toLocaleTimeString()}</p>
                <p>Size: ${size[0]}x${size[1]}</p>
            `;
        }

        // API functions
        async function refreshStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                if (data.system_info) {
                    document.getElementById('actions-count').textContent = data.interaction_count || 0;
                    document.getElementById('cpu-usage').textContent = Math.round(data.system_info.cpu_percent || 0) + '%';
                }
            } catch (error) {
                log(`Failed to refresh status: ${error.message}`, 'error');
            }
        }

        async function executeTask() {
            const task = document.getElementById('task-input').value;
            if (!task) {
                log('Please enter a task', 'error');
                return;
            }

            try {
                const response = await fetch('/api/task', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task })
                });
                const data = await response.json();
                if (data.error) {
                    log(`Task error: ${data.error}`, 'error');
                } else {
                    log(`Task started: ${task}`, 'info');
                    document.getElementById('task-input').value = '';
                }
            } catch (error) {
                log(`Failed to execute task: ${error.message}`, 'error');
            }
        }

        async function toggleAutonomous() {
            try {
                const response = await fetch('/api/autonomous', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enable: true })
                });
                const data = await response.json();
                log(`Autonomous mode: ${data.autonomous_mode ? 'started' : 'stopped'}`, 'info');
            } catch (error) {
                log(`Failed to toggle autonomous mode: ${error.message}`, 'error');
            }
        }

        async function takeScreenshot() {
            try {
                const response = await fetch('/api/screenshot');
                const data = await response.json();
                if (data.error) {
                    log(`Screenshot error: ${data.error}`, 'error');
                } else {
                    displayScreenshot(data.image, data.timestamp, data.size);
                    log('Screenshot taken', 'success');
                }
            } catch (error) {
                log(`Failed to take screenshot: ${error.message}`, 'error');
            }
        }

        async function analyzeScreen() {
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task: 'analyze the current desktop' })
                });
                const data = await response.json();
                if (data.error) {
                    log(`Analysis error: ${data.error}`, 'error');
                } else {
                    log(`AI Analysis: ${data.analysis.analysis || 'Analysis completed'}`, 'info');
                    if (data.analysis.suggested_action) {
                        log(`Suggested action: ${data.analysis.suggested_action.reasoning}`, 'info');
                    }
                }
            } catch (error) {
                log(`Failed to analyze screen: ${error.message}`, 'error');
            }
        }

        async function clickAt() {
            const x = parseInt(document.getElementById('click-x').value);
            const y = parseInt(document.getElementById('click-y').value);

            if (!x || !y) {
                log('Please enter valid coordinates', 'error');
                return;
            }

            try {
                const response = await fetch('/api/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ type: 'click', x, y })
                });
                const data = await response.json();
                if (data.error) {
                    log(`Click error: ${data.error}`, 'error');
                } else {
                    log(`Clicked at (${x}, ${y})`, 'success');
                }
            } catch (error) {
                log(`Failed to click: ${error.message}`, 'error');
            }
        }

        function requestScreenshot() {
            socket.emit('request_screenshot');
        }

        function toggleLiveMode() {
            isLiveMode = !isLiveMode;
            socket.emit('live_mode', { enabled: isLiveMode, interval: 2 });
            log(`Live mode ${isLiveMode ? 'enabled' : 'disabled'}`, 'info');
        }

        function refreshScreenshot() {
            takeScreenshot();
        }

        function emergencyStop() {
            fetch('/api/autonomous', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enable: false })
            });
            log('Emergency stop triggered', 'error');
        }

        function clearLog() {
            activityLog.innerHTML = '';
        }

        function exportLog() {
            const logText = activityLog.textContent;
            const blob = new Blob([logText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ai_desktop_log_${new Date().toISOString()}.txt`;
            a.click();
        }

        // Update uptime
        setInterval(() => {
            const uptimeSeconds = Math.floor((Date.now() - startTime) / 1000);
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;
            document.getElementById('uptime').textContent =
                `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }, 1000);

        // Refresh status periodically
        setInterval(refreshStatus, 5000);
    </script>
</body>
</html>
    \"\"\"

    dashboard_path = templates_dir / 'dashboard.html'
    if not dashboard_path.exists():
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)

def initialize_ai_controller():
    \"\"\"Initialize the AI controller\"\"\"
    global ai_controller

    try:
        ai_controller = AIDesktopController()
        logger.info(\"✅ AI Desktop Controller initialized successfully\")
        return True
    except Exception as e:
        logger.error(f\"❌ Failed to initialize AI Controller: {e}\")
        return False

def main():
    \"\"\"Main entry point for web interface\"\"\"
    import argparse

    parser = argparse.ArgumentParser(description=\"AI Desktop Controller Web Interface\")
    parser.add_argument(\"--host\", default=\"127.0.0.1\", help=\"Host to bind to\")
    parser.add_argument(\"--port\", type=int, default=8080, help=\"Port to bind to\")
    parser.add_argument(\"--debug\", action=\"store_true\", help=\"Enable debug mode\")
    args = parser.parse_args()

    # Create templates
    create_templates()

    # Initialize AI controller
    if not initialize_ai_controller():
        print(\"❌ Failed to initialize AI Controller. Check your config.json file.\")
        sys.exit(1)

    print(\"🚀 Starting AI Desktop Controller Web Interface\")
    print(f\"📱 Access the dashboard at: http://{args.host}:{args.port}\")
    print(\"🛑 Press Ctrl+C to stop\")

    try:
        socketio.run(
            app,
            host=args.host,
            port=args.port,
            debug=args.debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print(\"\\n👋 Shutting down AI Desktop Controller Web Interface\")
        if ai_controller:
            ai_controller.stop()
    except Exception as e:
        logger.error(f\"Web interface error: {e}\")
        sys.exit(1)

if __name__ == \"__main__\":
    main()