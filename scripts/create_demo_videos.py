#!/usr/bin/env python3
"""
GPL Demo Video Creator
Creates 4 demo videos showing different adaptation scenarios
"""

import asyncio
import cv2
import numpy as np
from pathlib import Path
import time
import sys

# Force unbuffered output
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__

sys.path.insert(0, '.')  # Docker runs from /app

from core.processors.hdr_processor import HDRProcessor
from telemetry.base import TelemetryFrame, TelemetryData, TelemetryType
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class DemoProfile:
    """Profile for a specific demo"""
    name: str
    description: str
    telemetry_sequence: List[Dict]
    

class DemoVideoCreator:
    """Creates demo videos with different telemetry profiles"""
    
    def __init__(self):
        self.input_video = "data/samples/sdr/1080p/swordsmith_0-5s_1080p.mp4"
        self.output_dir = Path("data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define demo profiles
        self.profiles = {
            "standard": DemoProfile(
                name="Standard HDR",
                description="Fixed parameters - no adaptation",
                telemetry_sequence=[
                    # Constant middle-ground values
                    {"time": 0.0, "light": 1000, "color_temp": 5000, "motion": 0.3},
                    {"time": 5.0, "light": 1000, "color_temp": 5000, "motion": 0.3}
                ]
            ),
            
            "light": DemoProfile(
                name="Light Adaptation",
                description="Adapts to ambient light changes",
                telemetry_sequence=[
                    # Dark room -> Normal -> Bright
                    {"time": 0.0, "light": 50, "color_temp": 5000, "motion": 0.3},
                    {"time": 1.5, "light": 50, "color_temp": 5000, "motion": 0.3},
                    {"time": 2.0, "light": 500, "color_temp": 5000, "motion": 0.3},
                    {"time": 3.5, "light": 500, "color_temp": 5000, "motion": 0.3},
                    {"time": 4.0, "light": 2000, "color_temp": 5000, "motion": 0.3},
                    {"time": 5.0, "light": 2000, "color_temp": 5000, "motion": 0.3}
                ]
            ),
            
            "color": DemoProfile(
                name="Color Temperature",
                description="Adapts to environmental color",
                telemetry_sequence=[
                    # Firelight -> Mixed -> Daylight
                    {"time": 0.0, "light": 500, "color_temp": 2700, "motion": 0.3},
                    {"time": 1.5, "light": 500, "color_temp": 2700, "motion": 0.3},
                    {"time": 2.0, "light": 500, "color_temp": 4000, "motion": 0.3},
                    {"time": 3.5, "light": 500, "color_temp": 4000, "motion": 0.3},
                    {"time": 4.0, "light": 500, "color_temp": 6500, "motion": 0.3},
                    {"time": 5.0, "light": 500, "color_temp": 6500, "motion": 0.3}
                ]
            ),
            
            "motion": DemoProfile(
                name="Motion Adaptation",
                description="Reduces processing during high motion",
                telemetry_sequence=[
                    # Low motion -> High motion (sparks) -> Medium
                    {"time": 0.0, "light": 500, "color_temp": 5000, "motion": 0.2},
                    {"time": 1.5, "light": 500, "color_temp": 5000, "motion": 0.2},
                    {"time": 2.0, "light": 500, "color_temp": 5000, "motion": 0.8},
                    {"time": 3.5, "light": 500, "color_temp": 5000, "motion": 0.8},
                    {"time": 4.0, "light": 500, "color_temp": 5000, "motion": 0.4},
                    {"time": 5.0, "light": 500, "color_temp": 5000, "motion": 0.4}
                ]
            )
        }
    
    def create_telemetry_frame(self, light: float, color_temp: float, motion: float) -> TelemetryFrame:
        """Create a telemetry frame with specified values"""
        frame = TelemetryFrame()
        
        frame.add_reading(TelemetryData(
            type=TelemetryType.AMBIENT_LIGHT,
            value=light,
            unit="lux"
        ))
        
        frame.add_reading(TelemetryData(
            type=TelemetryType.COLOR_TEMPERATURE,
            value=color_temp,
            unit="kelvin"
        ))
        
        frame.add_reading(TelemetryData(
            type=TelemetryType.MOTION,
            value=motion,
            unit="normalized"
        ))
        
        return frame
    
    def interpolate_telemetry(self, sequence: List[Dict], current_time: float) -> Tuple[float, float, float]:
        """Interpolate telemetry values for current time"""
        # Find the two points to interpolate between
        prev = sequence[0]
        next = sequence[0]
        
        for i in range(len(sequence) - 1):
            if sequence[i]["time"] <= current_time <= sequence[i + 1]["time"]:
                prev = sequence[i]
                next = sequence[i + 1]
                break
            elif current_time > sequence[i + 1]["time"]:
                prev = sequence[i + 1]
                next = sequence[i + 1]
        
        # If same point, no interpolation needed
        if prev["time"] == next["time"]:
            return prev["light"], prev["color_temp"], prev["motion"]
        
        # Linear interpolation
        t = (current_time - prev["time"]) / (next["time"] - prev["time"])
        light = prev["light"] + t * (next["light"] - prev["light"])
        color_temp = prev["color_temp"] + t * (next["color_temp"] - prev["color_temp"])
        motion = prev["motion"] + t * (next["motion"] - prev["motion"])
        
        return light, color_temp, motion
    
    async def process_video(self, profile_name: str):
        """Process video with a specific profile"""
        profile = self.profiles[profile_name]
        output_path = self.output_dir / f"demo_{profile_name}_adaptation.mp4"
        
        print(f"\n{'='*60}")
        print(f"Creating {profile.name} Demo")
        print(f"Description: {profile.description}")
        print(f"Output: {output_path}")
        print(f"{'='*60}\n")
        
        # Initialize processor with appropriate preset
        # Use balanced preset for better quality (same as original demo)
        processor = HDRProcessor(preset="balanced")
        
        # Open video
        cap = cv2.VideoCapture(self.input_video)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Create output writer - try direct MP4 with better quality
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate current time in video
            current_time = frame_count / fps
            
            # Get telemetry for this time
            light, color_temp, motion = self.interpolate_telemetry(
                profile.telemetry_sequence, current_time
            )
            
            # Create telemetry frame
            telemetry = self.create_telemetry_frame(light, color_temp, motion)
            
            # Process frame
            if profile_name == "standard":
                # For standard, ignore telemetry (use fixed params)
                enhanced_frame, metrics = processor.process_frame(frame, None)
            else:
                # For others, use telemetry-driven adaptation
                enhanced_frame, metrics = processor.process_frame(frame, telemetry)
            
            # Write frame
            out.write(enhanced_frame)
            
            frame_count += 1
            
            # Progress update
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% | "
                      f"Light: {light:.0f} lux | "
                      f"Color: {color_temp:.0f}K | "
                      f"Motion: {motion*100:.0f}% | "
                      f"Latency: {metrics['process_time_ms']:.1f}ms", flush=True)
        
        # Cleanup
        cap.release()
        out.release()
        
        # Summary
        elapsed = time.time() - start_time
        avg_fps = frame_count / elapsed
        print(f"\n✅ {profile.name} complete!")
        print(f"   Processed {frame_count} frames in {elapsed:.1f}s ({avg_fps:.1f} FPS)")
        print(f"   Output: {output_path}")
    
    async def create_all_demos(self):
        """Create all demo videos"""
        print("\n" + "="*60)
        print("GPL DEMO VIDEO CREATOR")
        print("Creating 4 demo videos for hackathon")
        print("="*60)
        
        # Check input exists
        if not Path(self.input_video).exists():
            print(f"\n❌ ERROR: Input video not found: {self.input_video}")
            print("Please ensure the 5-second clip exists at:")
            print(f"  {Path(self.input_video).absolute()}")
            return
        
        # Process each profile
        for profile_name in ["standard", "light", "color", "motion"]:
            await self.process_video(profile_name)
        
        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETE!")
        print("\nDemo videos created:")
        for profile_name, profile in self.profiles.items():
            output_path = self.output_dir / f"demo_{profile_name}_adaptation.mp4"
            if output_path.exists():
                print(f"  ✓ {profile.name}: {output_path}")
        print("\nReady for hackathon presentation! 🚀")
        print("="*60 + "\n")


async def main():
    creator = DemoVideoCreator()
    await creator.create_all_demos()


if __name__ == "__main__":
    asyncio.run(main())