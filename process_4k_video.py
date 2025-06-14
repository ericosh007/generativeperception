import asyncio
import cv2
import sys
import time

sys.path.insert(0, '.')

from core.processors.hdr_processor import HDRProcessor
from telemetry.collectors.system_telemetry import SystemTelemetryCollector

async def process_4k():
    hdr_processor = HDRProcessor(preset="performance")
    telemetry_collector = SystemTelemetryCollector(use_simulated=True)
    await telemetry_collector.start()
    
    input_path = "data/samples/sdr/Sony Swordsmith HDR UHD 4K Demo_sdr.mp4"
    output_path = "data/output/swordsmith_enhanced_4k.mp4"
    
    print("Processing 4K video...")
    print(f"Input: {input_path}")
    
    cap = cv2.VideoCapture(input_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Resolution: {width}x{height}, Total frames: {total_frames}")
    
    fourcc = cv2.VideoWriter_fourcc(*'h264')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        telemetry = await telemetry_collector.get_current_telemetry()
        enhanced_frame, metrics = hdr_processor.process_frame(frame, telemetry)
        out.write(enhanced_frame)
        
        frame_count += 1
        if frame_count % 30 == 0:
            print(f"Progress: {frame_count}/{total_frames} ({100*frame_count/total_frames:.1f}%)")
    
    cap.release()
    out.release()
    await telemetry_collector.stop()
    
    print(f"Done! Processed {frame_count} frames")
    print(f"Output: {output_path}")

asyncio.run(process_4k())
