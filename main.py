"""
GPL - Generative Perception Layers
Main application entry point
"""

import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import cv2
import numpy as np
from pathlib import Path
import json

from config.settings import settings
from core.processors.hdr_processor import HDRProcessor
from telemetry.collectors.system_telemetry import SystemTelemetryCollector
from telemetry.sensors.simulated import SimulatedSensors
from web.api.routes import api_router
from web.streaming.webrtc_server import WebRTCServer


class GPLApplication:
    """Main GPL Application"""
    
    def __init__(self):
        self.app = FastAPI(
            title=settings.app_name,
            version=settings.app_version,
            debug=settings.debug
        )
        
        # Core components
        self.hdr_processor = HDRProcessor(preset=settings.hdr_quality_preset)
        self.telemetry_collector = SystemTelemetryCollector()
        self.stream_server = WebRTCServer()
        
        # Setup routes and middleware
        self._setup_routes()
        self._setup_websocket()
        
        # State
        self.is_processing = False
        self.current_source = None
        
    def _setup_routes(self):
        """Setup API routes"""
        self.app.include_router(api_router, prefix="/api")
        
        # Serve static files
        static_dir = Path("web/static")
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        @self.app.get("/")
        async def root():
            return HTMLResponse(self._get_index_html())
    
    def _setup_websocket(self):
        """Setup WebSocket endpoints"""
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            
            try:
                while True:
                    # Send telemetry updates
                    telemetry = await self.telemetry_collector.get_current_telemetry()
                    await websocket.send_json({
                        "type": "telemetry",
                        "data": telemetry.to_dict() if telemetry else {}
                    })
                    
                    # Send processing metrics
                    if self.is_processing:
                        await websocket.send_json({
                            "type": "metrics",
                            "data": {
                                "fps": self.hdr_processor.frame_count,
                                "latency": self.hdr_processor.total_time / max(1, self.hdr_processor.frame_count)
                            }
                        })
                    
                    await asyncio.sleep(0.1)  # 10Hz updates
                    
            except Exception as e:
                print(f"WebSocket error: {e}")
    
    async def start_processing(self, source: str):
        """Start HDR processing on video source"""
        self.is_processing = True
        self.current_source = source
        
        # Start telemetry collection
        await self.telemetry_collector.start()
        
        # Open video source
        if source == "webcam":
            cap = cv2.VideoCapture(0)
        else:
            cap = cv2.VideoCapture(source)
        
        try:
            while self.is_processing:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Get current telemetry
                telemetry = await self.telemetry_collector.collect_frame()
                
                # Process frame
                processed, metrics = self.hdr_processor.process_frame(frame, telemetry)
                
                # Stream processed frame
                await self.stream_server.send_frame(processed)
                
                # Small delay to control frame rate
                await asyncio.sleep(1.0 / settings.target_fps)
                
        finally:
            cap.release()
            await self.telemetry_collector.stop()
            self.is_processing = False
    
    def _get_index_html(self) -> str:
        """Generate index HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>GPL - Generative Perception Layers</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #0a0a0a;
            color: #ffffff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 40px 0;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            margin: -20px -20px 40px -20px;
        }
        h1 {
            margin: 0;
            font-size: 3em;
            font-weight: 300;
            letter-spacing: 2px;
        }
        .subtitle {
            margin-top: 10px;
            opacity: 0.8;
            font-size: 1.2em;
        }
        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
            margin-top: 40px;
        }
        .video-container {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            position: relative;
        }
        #video-display {
            width: 100%;
            height: auto;
            border-radius: 8px;
            background: #000;
        }
        .telemetry-panel {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
        }
        .telemetry-item {
            margin-bottom: 20px;
            padding: 15px;
            background: #252525;
            border-radius: 8px;
        }
        .telemetry-label {
            font-size: 0.9em;
            opacity: 0.7;
            margin-bottom: 5px;
        }
        .telemetry-value {
            font-size: 1.8em;
            font-weight: 300;
        }
        .controls {
            margin-top: 30px;
            text-align: center;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            font-size: 1.1em;
            border-radius: 30px;
            cursor: pointer;
            margin: 0 10px;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .status {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            background: #252525;
            border-radius: 8px;
        }
        .status.active {
            background: #1a472a;
            color: #4ade80;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>GENERATIVE PERCEPTION LAYERS</h1>
            <div class="subtitle">Dynamic HDR Enhancement with Telemetric Intelligence</div>
        </div>
        
        <div class="grid">
            <div class="video-container">
                <video id="video-display" autoplay muted></video>
                <div class="status" id="status">Ready</div>
            </div>
            
            <div class="telemetry-panel">
                <h2>Live Telemetry</h2>
                
                <div class="telemetry-item">
                    <div class="telemetry-label">Ambient Light</div>
                    <div class="telemetry-value" id="ambient-light">-- lux</div>
                </div>
                
                <div class="telemetry-item">
                    <div class="telemetry-label">Color Temperature</div>
                    <div class="telemetry-value" id="color-temp">-- K</div>
                </div>
                
                <div class="telemetry-item">
                    <div class="telemetry-label">Motion Level</div>
                    <div class="telemetry-value" id="motion">--%</div>
                </div>
                
                <div class="telemetry-item">
                    <div class="telemetry-label">Processing Latency</div>
                    <div class="telemetry-value" id="latency">-- ms</div>
                </div>
                
                <div class="telemetry-item">
                    <div class="telemetry-label">Frame Rate</div>
                    <div class="telemetry-value" id="fps">-- fps</div>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <button onclick="startWebcam()">Start Webcam</button>
            <button onclick="uploadVideo()">Upload Video</button>
            <button onclick="stop()">Stop</button>
        </div>
    </div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8000/ws');
        const status = document.getElementById('status');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'telemetry') {
                updateTelemetry(data.data);
            } else if (data.type === 'metrics') {
                updateMetrics(data.data);
            }
        };
        
        function updateTelemetry(telemetry) {
            if (telemetry.data) {
                if (telemetry.data.ambient_light) {
                    document.getElementById('ambient-light').textContent = 
                        `${telemetry.data.ambient_light.value.toFixed(0)} lux`;
                }
                if (telemetry.data.color_temperature) {
                    document.getElementById('color-temp').textContent = 
                        `${telemetry.data.color_temperature.value.toFixed(0)} K`;
                }
                if (telemetry.data.motion) {
                    document.getElementById('motion').textContent = 
                        `${(telemetry.data.motion.value * 100).toFixed(0)}%`;
                }
            }
        }
        
        function updateMetrics(metrics) {
            document.getElementById('latency').textContent = 
                `${metrics.latency.toFixed(1)} ms`;
            document.getElementById('fps').textContent = 
                `${metrics.fps.toFixed(0)} fps`;
        }
        
        async function startWebcam() {
            status.textContent = 'Starting webcam...';
            status.classList.add('active');
            
            const response = await fetch('/api/process/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({source: 'webcam'})
            });
            
            if (response.ok) {
                // Setup WebRTC connection for video stream
                setupWebRTC();
            }
        }
        
        async function stop() {
            status.textContent = 'Stopping...';
            status.classList.remove('active');
            
            await fetch('/api/process/stop', {method: 'POST'});
        }
        
        function setupWebRTC() {
            // WebRTC setup code here
            // This would connect to the stream server
            console.log('Setting up WebRTC connection...');
        }
    </script>
</body>
</html>
        """
    
    async def run(self):
        """Run the application"""
        config = uvicorn.Config(
            self.app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower()
        )
        server = uvicorn.Server(config)
        await server.serve()


async def main():
    """Main entry point"""
    app = GPLApplication()
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())