"""
GPL Demo - Quick Demo Runner
Simplified version for immediate Docker deployment
"""

import asyncio
import cv2
import numpy as np
from pathlib import Path
import time
import sys

# Add the current directory to Python path
sys.path.insert(0, '.')

from config.settings import settings
from core.processors.hdr_processor import HDRProcessor
from telemetry.collectors.system_telemetry import SystemTelemetryCollector


async def create_demo_video():
    """Create a simple demo video if none exists"""
    demo_path = Path("data/samples/demo_video.mp4")
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not demo_path.exists():
        print("Creating demo video...")
        # Create a synthetic video with color gradients
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(demo_path), fourcc, 30.0, (1920, 1080))
        
        for frame_num in range(150):  # 5 seconds at 30fps
            # Create gradient frame
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            
            # Add color gradients
            for y in range(1080):
                for x in range(1920):
                    frame[y, x] = [
                        int(255 * (x / 1920)),  # Red gradient
                        int(255 * (y / 1080)),  # Green gradient
                        int(255 * ((frame_num % 60) / 60))  # Blue pulse
                    ]
            
            # Add text
            cv2.putText(frame, f"GPL Demo Frame {frame_num}", (50, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            
            out.write(frame)
        
        out.release()
        print(f"Demo video created: {demo_path}")
    
    return str(demo_path)


async def run_demo():
    """Run the HDR enhancement demo"""
    print("\n" + "="*60)
    print("GPL - Generative Perception Layers")
    print("HDR Enhancement Demo with Telemetry")
    print("="*60 + "\n")
    
    # Initialize components
    print("Initializing HDR processor...")
    hdr_processor = HDRProcessor(preset="balanced")
    
    print("Starting telemetry collection...")
    telemetry_collector = SystemTelemetryCollector(use_simulated=True)
    await telemetry_collector.start()
    
    # Create or get demo video
    video_path = await create_demo_video()
    
    # Create output directory
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Open video
    print(f"\nProcessing video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Create output video writer
    output_path = output_dir / "demo_enhanced.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    print(f"Video info: {width}x{height} @ {fps}fps, {total_frames} frames")
    print(f"Output will be saved to: {output_path}")
    print("\nProcessing...")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Get current telemetry
            telemetry = await telemetry_collector.get_current_telemetry()
            
            # Process frame
            enhanced_frame, metrics = hdr_processor.process_frame(frame, telemetry)
            
            # Write output
            out.write(enhanced_frame)
            
            frame_count += 1
            
            # Print progress
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps_actual = frame_count / elapsed
                progress = (frame_count / total_frames) * 100
                
                if telemetry:
                    light = telemetry.get_value(telemetry.data.get(list(telemetry.data.keys())[0]).type) if telemetry.data else 0
                    print(f"Progress: {progress:.1f}% | FPS: {fps_actual:.1f} | "
                          f"Latency: {metrics['process_time_ms']:.1f}ms | "
                          f"Light: {light:.0f} lux")
                else:
                    print(f"Progress: {progress:.1f}% | FPS: {fps_actual:.1f} | "
                          f"Latency: {metrics['process_time_ms']:.1f}ms")
    
    finally:
        # Cleanup
        cap.release()
        out.release()
        await telemetry_collector.stop()
    
    # Summary
    total_time = time.time() - start_time
    avg_fps = frame_count / total_time
    avg_latency = hdr_processor.total_time / max(1, hdr_processor.frame_count)
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print(f"Processed {frame_count} frames in {total_time:.1f} seconds")
    print(f"Average FPS: {avg_fps:.1f}")
    print(f"Average latency: {avg_latency:.1f}ms per frame")
    print(f"Output saved to: {output_path}")
    print("="*60 + "\n")
    
    # Also create a comparison image
    print("Creating comparison image...")
    cap_orig = cv2.VideoCapture(video_path)
    cap_enh = cv2.VideoCapture(str(output_path))
    
    # Get middle frame
    middle_frame = total_frames // 2
    cap_orig.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
    cap_enh.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
    
    ret1, orig_frame = cap_orig.read()
    ret2, enh_frame = cap_enh.read()
    
    if ret1 and ret2:
        # Create side-by-side comparison
        comparison = np.hstack([orig_frame, enh_frame])
        
        # Add labels
        cv2.putText(comparison, "Original", (50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        cv2.putText(comparison, "GPL Enhanced", (width + 50, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        
        comparison_path = output_dir / "demo_comparison.jpg"
        cv2.imwrite(str(comparison_path), comparison)
        print(f"Comparison saved to: {comparison_path}")
    
    cap_orig.release()
    cap_enh.release()


if __name__ == "__main__":
    asyncio.run(run_demo())