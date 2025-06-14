#!/usr/bin/env python3
"""
GPL Demo Runner
Showcases telemetry-driven HDR enhancement with your video samples
"""

import asyncio
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.processors.hdr_processor import HDRProcessor
from telemetry.base import TelemetryFrame, TelemetryData, TelemetryType
import cv2
import numpy as np
from datetime import datetime, timedelta


class DemoRunner:
    """Runs GPL demos with your video samples"""
    
    def __init__(self):
        self.hdr_processor = HDRProcessor(preset="balanced")
        self.telemetry_profiles = self._load_telemetry_profiles()
        
    def _load_telemetry_profiles(self) -> dict:
        """Load telemetry profiles"""
        profile_path = Path("data/samples/telemetry_profiles.json")
        if profile_path.exists():
            with open(profile_path) as f:
                return json.load(f)
        return {}
    
    def create_telemetry_frame(self, profile_data: dict, elapsed_seconds: float) -> TelemetryFrame:
        """Create telemetry frame from profile data"""
        frame = TelemetryFrame()
        
        # Find the right telemetry point based on time
        sequence = profile_data.get("telemetry_sequence", [])
        current_data = sequence[0] if sequence else {}
        
        for point in sequence:
            if point["time"] <= elapsed_seconds:
                current_data = point
            else:
                break
        
        # Add telemetry readings
        frame.add_reading(TelemetryData(
            type=TelemetryType.AMBIENT_LIGHT,
            value=current_data.get("ambient_light", 500),
            unit="lux"
        ))
        
        frame.add_reading(TelemetryData(
            type=TelemetryType.COLOR_TEMPERATURE,
            value=current_data.get("color_temperature", 5000),
            unit="kelvin"
        ))
        
        frame.add_reading(TelemetryData(
            type=TelemetryType.MOTION,
            value=current_data.get("motion", 0.3),
            unit="normalized"
        ))
        
        return frame
    
    async def run_comparison_demo(self, video_name: str):
        """Run side-by-side comparison demo"""
        print(f"\n{'='*60}")
        print(f"Running Demo: {video_name}")
        print(f"{'='*60}\n")
        
        # Get paths
        sdr_path = f"data/samples/sdr/{video_name}_sdr.mp4"
        profile_key = video_name
        
        if not Path(sdr_path).exists():
            print(f"SDR video not found: {sdr_path}")
            return
            
        # Get profile
        profile = self.telemetry_profiles.get("profiles", {}).get(profile_key, {})
        if not profile:
            print(f"No telemetry profile for: {video_name}")
            return
            
        print(f"Profile: {profile['name']}")
        print(f"Description: {profile['description']}\n")
        
        # Open video
        cap = cv2.VideoCapture(sdr_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Create output window
        cv2.namedWindow("GPL Demo - Press 'q' to skip", cv2.WINDOW_NORMAL)
        
        start_time = datetime.now()
        frame_count = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Calculate elapsed time
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Get telemetry for this moment
            telemetry = self.create_telemetry_frame(profile, elapsed)
            
            # Process frame
            enhanced, metrics = self.hdr_processor.process_frame(frame, telemetry)
            
            # Create comparison view
            h, w = frame.shape[:2]
            comparison = np.zeros((h, w*2 + 20, 3), dtype=np.uint8)
            
            # Original SDR
            comparison[:, :w] = frame
            
            # Divider
            comparison[:, w:w+20] = 80
            
            # Enhanced
            comparison[:, w+20:] = enhanced
            
            # Add labels
            cv2.putText(comparison, "Original SDR", (20, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(comparison, "GPL Enhanced", (w+40, 40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Add telemetry info
            telemetry_text = [
                f"Light: {telemetry.get_value(TelemetryType.AMBIENT_LIGHT):.0f} lux",
                f"Temp: {telemetry.get_value(TelemetryType.COLOR_TEMPERATURE):.0f}K",
                f"Motion: {telemetry.get_value(TelemetryType.MOTION):.1f}",
                f"Latency: {metrics['process_time_ms']:.1f}ms"
            ]
            
            y_offset = h - 120
            for i, text in enumerate(telemetry_text):
                cv2.putText(comparison, text, (w+40, y_offset + i*30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show
            cv2.imshow("GPL Demo - Press 'q' to skip", comparison)
            
            # Check for quit
            if cv2.waitKey(int(1000/fps)) & 0xFF == ord('q'):
                break
                
            frame_count += 1
            
            # Print progress
            if frame_count % 30 == 0:
                print(f"Frame {frame_count}: {metrics['process_time_ms']:.1f}ms | "
                      f"Params: exposure={metrics['params']['exposure']:.2f}, "
                      f"saturation={metrics['params']['saturation']:.2f}")
        
        cap.release()
        cv2.destroyAllWindows()
        
        print(f"\nDemo complete for: {video_name}")
        print(f"Average latency: {self.hdr_processor.total_time / max(1, self.hdr_processor.frame_count):.1f}ms")
    
    async def run_all_demos(self):
        """Run all available demos"""
        videos = ["food_fizzle", "swordsmith", "whale_tonga"]
        
        print("\n" + "="*60)
        print("GPL - Generative Perception Layers")
        print("Telemetry-Driven HDR Enhancement Demo")
        print("="*60)
        print("\nThis demo shows how telemetry data dynamically adjusts")
        print("HDR processing parameters in real-time.\n")
        print("Press 'q' to skip to next video\n")
        
        for video in videos:
            await self.run_comparison_demo(video)
            
            # Pause between demos
            print("\nPress Enter for next demo...")
            input()
        
        print("\n" + "="*60)
        print("Demo Complete!")
        print("="*60)


async def main():
    runner = DemoRunner()
    await runner.run_all_demos()


if __name__ == "__main__":
    asyncio.run(main())