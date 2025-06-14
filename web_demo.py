"""
GPL Web Demo - Browser-based side-by-side comparison
Real-time HDR enhancement with telemetry visualization
"""

import asyncio
import cv2
import numpy as np
import base64
import json
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Optional
import sys

sys.path.insert(0, '.')

from config.settings import settings
from core.processors.hdr_processor import HDRProcessor
from telemetry.collectors.system_telemetry import SystemTelemetryCollector


class WebDemo:
    def __init__(self):
        self.app = FastAPI(title="GPL Web Demo")
        self.hdr_processor = HDRProcessor(preset="balanced")
        self.telemetry_collector = SystemTelemetryCollector(use_simulated=True)
        self.is_processing = False
        self.websocket_clients = []
        
        # Setup routes
        self.setup_routes()
        
    def setup_routes(self):
        @self.app.get("/")
        async def index():
            return HTMLResponse(self.get_index_html())
            
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.websocket_clients.append(websocket)
            
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
                
        @self.app.post("/start")
        async def start_processing():
            if not self.is_processing:
                asyncio.create_task(self.process_video())
            return {"status": "started"}
            
        @self.app.post("/stop")
        async def stop_processing():
            self.is_processing = False
            return {"status": "stopped"}
            
        @self.app.get("/demo-video")
        async def get_demo_video():
            video_path = await self.create_demo_video()
            return FileResponse(video_path)
    
    async def create_demo_video(self):
        """Create or return demo video"""
        demo_path = Path("data/samples/demo_video.mp4")
        demo_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not demo_path.exists():
            # Create a test pattern video
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(str(demo_path), fourcc, 30.0, (1280, 720))
            
            for frame_num in range(150):  # 5 seconds
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                
                # Create test pattern
                for y in range(720):
                    for x in range(1280):
                        # Create zones with different characteristics
                        if x < 320:  # Dark zone
                            base = 30
                        elif x < 640:  # Mid zone
                            base = 128
                        elif x < 960:  # Bright zone
                            base = 200
                        else:  # Color gradient zone
                            base = 128
                            
                        if x >= 960:
                            frame[y, x] = [
                                int(base + 50 * np.sin(frame_num * 0.1)),
                                int(base + 50 * np.cos(frame_num * 0.1)),
                                base
                            ]
                        else:
                            gray = base + int(20 * np.sin(y * 0.02))
                            frame[y, x] = [gray, gray, gray]
                
                # Add moving elements
                circle_x = int(640 + 300 * np.sin(frame_num * 0.05))
                circle_y = int(360 + 200 * np.cos(frame_num * 0.05))
                cv2.circle(frame, (circle_x, circle_y), 50, (255, 128, 0), -1)
                
                # Add text
                cv2.putText(frame, f"GPL Test Pattern - Frame {frame_num}", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                out.write(frame)
            
            out.release()
            
        return str(demo_path)
    
    async def process_video(self):
        """Process video and stream results to browser"""
        self.is_processing = True
        
        # Start telemetry
        await self.telemetry_collector.start()
        
        # Get video
        video_path = await self.create_demo_video()
        cap = cv2.VideoCapture(video_path)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_delay = 1.0 / fps
        
        try:
            while self.is_processing and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # Loop video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                # Get telemetry
                telemetry = await self.telemetry_collector.get_current_telemetry()
                
                # Process frame
                enhanced_frame, metrics = self.hdr_processor.process_frame(frame, telemetry)
                
                # Create side-by-side comparison
                comparison = np.hstack([frame, enhanced_frame])
                
                # Add labels
                h, w = frame.shape[:2]
                label_bg = np.zeros((60, w*2, 3), dtype=np.uint8)
                cv2.putText(label_bg, "Original SDR", (20, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
                cv2.putText(label_bg, "GPL Enhanced", (w + 20, 40),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
                
                # Stack labels on top
                display_frame = np.vstack([label_bg, comparison])
                
                # Resize for web display
                display_frame = cv2.resize(display_frame, (1280, 420))
                
                # Convert to base64
                _, buffer = cv2.imencode('.jpg', display_frame, 
                                        [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Prepare telemetry data
                telemetry_data = {
                    "ambient_light": 0,
                    "color_temp": 0,
                    "motion": 0,
                    "latency": metrics['process_time_ms'],
                    "exposure": metrics['params']['exposure'],
                    "contrast": metrics['params']['contrast'],
                    "saturation": metrics['params']['saturation']
                }
                
                if telemetry and telemetry.data:
                    telemetry_values = telemetry.get_latest_values()
                    for t_type, value in telemetry_values.items():
                        if t_type.value == "ambient_light":
                            telemetry_data["ambient_light"] = value
                        elif t_type.value == "color_temperature":
                            telemetry_data["color_temp"] = value
                        elif t_type.value == "motion":
                            telemetry_data["motion"] = value
                
                # Send to all connected clients
                message = json.dumps({
                    "type": "frame",
                    "data": frame_base64,
                    "telemetry": telemetry_data
                })
                
                disconnected = []
                for client in self.websocket_clients:
                    try:
                        await client.send_text(message)
                    except:
                        disconnected.append(client)
                
                # Remove disconnected clients
                for client in disconnected:
                    self.websocket_clients.remove(client)
                
                # Control frame rate
                await asyncio.sleep(frame_delay)
                
        finally:
            cap.release()
            await self.telemetry_collector.stop()
            self.is_processing = False
    
    def get_index_html(self):
        return """
<!DOCTYPE html>
<html>
<head>
    <title>GPL - Real-time HDR Enhancement Demo</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #fff;
            overflow-x: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 20px rgba(0,0,0,0.5);
        }
        
        h1 {
            font-size: 2.5em;
            font-weight: 300;
            letter-spacing: 2px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .video-container {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }
        
        #video-display {
            width: 100%;
            border-radius: 8px;
            background: #000;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .telemetry-card {
            background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .telemetry-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        .telemetry-label {
            font-size: 0.9em;
            color: #888;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .telemetry-value {
            font-size: 2em;
            font-weight: 300;
            color: #fff;
            margin-bottom: 5px;
        }
        
        .telemetry-bar {
            height: 4px;
            background: #333;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .telemetry-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }
        
        .controls {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 30px 0;
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1em;
            border-radius: 30px;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: 500;
            letter-spacing: 1px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            background: #444;
            cursor: not-allowed;
            box-shadow: none;
        }
        
        .status {
            text-align: center;
            padding: 10px 20px;
            background: #252525;
            border-radius: 20px;
            display: inline-block;
            margin: 20px auto;
            transition: all 0.3s;
        }
        
        .status.active {
            background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
            color: #4ade80;
            box-shadow: 0 4px 20px rgba(74, 222, 128, 0.3);
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }
        
        .spinner {
            border: 3px solid #333;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .info-section {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 30px;
            margin: 30px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin-top: 20px;
        }
        
        .info-item h3 {
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .info-item p {
            color: #aaa;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>GENERATIVE PERCEPTION LAYERS</h1>
        <div class="subtitle">Real-time Telemetry-Driven HDR Enhancement</div>
    </div>
    
    <div class="container">
        <div class="controls">
            <button id="startBtn" onclick="startProcessing()">Start Demo</button>
            <button id="stopBtn" onclick="stopProcessing()" disabled>Stop</button>
        </div>
        
        <div style="text-align: center;">
            <div class="status" id="status">Ready to start</div>
        </div>
        
        <div class="video-container">
            <div id="video-display">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Click "Start Demo" to begin</p>
                </div>
            </div>
        </div>
        
        <div class="telemetry-grid">
            <div class="telemetry-card">
                <div class="telemetry-label">Ambient Light</div>
                <div class="telemetry-value" id="ambient-light">-- lux</div>
                <div class="telemetry-bar">
                    <div class="telemetry-bar-fill" id="light-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="telemetry-card">
                <div class="telemetry-label">Color Temperature</div>
                <div class="telemetry-value" id="color-temp">-- K</div>
                <div class="telemetry-bar">
                    <div class="telemetry-bar-fill" id="temp-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="telemetry-card">
                <div class="telemetry-label">Motion Level</div>
                <div class="telemetry-value" id="motion">--%</div>
                <div class="telemetry-bar">
                    <div class="telemetry-bar-fill" id="motion-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="telemetry-card">
                <div class="telemetry-label">Processing Latency</div>
                <div class="telemetry-value" id="latency">-- ms</div>
            </div>
            
            <div class="telemetry-card">
                <div class="telemetry-label">Exposure Adjust</div>
                <div class="telemetry-value" id="exposure">--</div>
            </div>
            
            <div class="telemetry-card">
                <div class="telemetry-label">Saturation Boost</div>
                <div class="telemetry-value" id="saturation">--</div>
            </div>
        </div>
        
        <div class="info-section">
            <h2>How It Works</h2>
            <div class="info-grid">
                <div class="info-item">
                    <h3>🌞 Dynamic Light Adaptation</h3>
                    <p>The system simulates changing ambient light conditions and adjusts HDR parameters in real-time to optimize viewing.</p>
                </div>
                <div class="info-item">
                    <h3>🎨 Color Temperature Correction</h3>
                    <p>White balance automatically adjusts based on simulated color temperature sensors, from warm tungsten to cool daylight.</p>
                </div>
                <div class="info-item">
                    <h3>🏃 Motion-Aware Processing</h3>
                    <p>Processing intensity adapts to motion levels - reducing artifacts during fast movement while enhancing detail in static scenes.</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let isProcessing = false;
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onopen = () => {
                console.log('WebSocket connected');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'frame') {
                    // Update video display
                    const img = document.getElementById('video-img');
                    if (!img) {
                        document.getElementById('video-display').innerHTML = 
                            '<img id="video-img" style="width: 100%; height: auto;">';
                    }
                    document.getElementById('video-img').src = 'data:image/jpeg;base64,' + data.data;
                    
                    // Update telemetry
                    updateTelemetry(data.telemetry);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                if (isProcessing) {
                    setTimeout(connectWebSocket, 1000);
                }
            };
        }
        
        function updateTelemetry(telemetry) {
            // Update values
            document.getElementById('ambient-light').textContent = 
                Math.round(telemetry.ambient_light) + ' lux';
            document.getElementById('color-temp').textContent = 
                Math.round(telemetry.color_temp) + ' K';
            document.getElementById('motion').textContent = 
                Math.round(telemetry.motion * 100) + '%';
            document.getElementById('latency').textContent = 
                telemetry.latency.toFixed(1) + ' ms';
            document.getElementById('exposure').textContent = 
                telemetry.exposure.toFixed(2) + 'x';
            document.getElementById('saturation').textContent = 
                telemetry.saturation.toFixed(2) + 'x';
            
            // Update progress bars
            const lightPercent = Math.min(100, (telemetry.ambient_light / 5000) * 100);
            document.getElementById('light-bar').style.width = lightPercent + '%';
            
            const tempPercent = ((telemetry.color_temp - 2000) / 6000) * 100;
            document.getElementById('temp-bar').style.width = tempPercent + '%';
            
            document.getElementById('motion-bar').style.width = (telemetry.motion * 100) + '%';
        }
        
        async function startProcessing() {
            if (isProcessing) return;
            
            isProcessing = true;
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            document.getElementById('status').textContent = 'Processing...';
            document.getElementById('status').classList.add('active');
            
            // Connect WebSocket
            connectWebSocket();
            
            // Start processing
            const response = await fetch('/start', { method: 'POST' });
            const data = await response.json();
            console.log('Processing started:', data);
        }
        
        async function stopProcessing() {
            isProcessing = false;
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('status').textContent = 'Stopped';
            document.getElementById('status').classList.remove('active');
            
            // Stop processing
            await fetch('/stop', { method: 'POST' });
            
            // Close WebSocket
            if (ws) {
                ws.close();
                ws = null;
            }
        }
    </script>
</body>
</html>
        """
    
    async def run(self):
        """Run the web demo"""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    demo = WebDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())