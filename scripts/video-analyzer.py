#!/usr/bin/env python3
"""
GPL Video Analyzer
Analyzes HDR/SDR video pairs and generates telemetry recommendations
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
from dataclasses import dataclass
import argparse


@dataclass
class VideoStats:
    """Statistics for a video"""
    filename: str
    resolution: Tuple[int, int]
    fps: float
    frame_count: int
    avg_brightness: float
    brightness_range: Tuple[float, float]
    avg_saturation: float
    dynamic_range: float
    peak_brightness: float
    shadow_detail: float


class VideoAnalyzer:
    """Analyzes video characteristics for HDR optimization"""
    
    def __init__(self):
        self.sample_frames = 30  # Sample every 30 frames
        
    def analyze_video(self, video_path: str) -> VideoStats:
        """Analyze a video file"""
        print(f"Analyzing: {video_path}")
        cap = cv2.VideoCapture(video_path)
        
        # Get basic info
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Collect samples
        brightness_values = []
        saturation_values = []
        highlights = []
        shadows = []
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % self.sample_frames == 0:
                # Convert to different color spaces for analysis
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
                
                # Brightness (L channel in LAB)
                brightness = lab[:, :, 0].mean()
                brightness_values.append(brightness)
                
                # Saturation (S channel in HSV)
                saturation = hsv[:, :, 1].mean()
                saturation_values.append(saturation)
                
                # Highlights and shadows
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                highlights.append(np.percentile(gray, 95))
                shadows.append(np.percentile(gray, 5))
                
            frame_idx += 1
            
            # Progress
            if frame_idx % 100 == 0:
                print(f"  Progress: {frame_idx}/{frame_count} frames")
        
        cap.release()
        
        # Calculate statistics
        stats = VideoStats(
            filename=Path(video_path).name,
            resolution=(width, height),
            fps=fps,
            frame_count=frame_count,
            avg_brightness=np.mean(brightness_values),
            brightness_range=(np.min(brightness_values), np.max(brightness_values)),
            avg_saturation=np.mean(saturation_values),
            dynamic_range=np.mean(highlights) - np.mean(shadows),
            peak_brightness=np.max(highlights),
            shadow_detail=np.mean(shadows)
        )
        
        return stats
    
    def compare_hdr_sdr(self, hdr_stats: VideoStats, sdr_stats: VideoStats) -> Dict:
        """Compare HDR and SDR versions"""
        return {
            "brightness_difference": hdr_stats.avg_brightness - sdr_stats.avg_brightness,
            "saturation_difference": hdr_stats.avg_saturation - sdr_stats.avg_saturation,
            "dynamic_range_ratio": hdr_stats.dynamic_range / max(1, sdr_stats.dynamic_range),
            "highlight_headroom": hdr_stats.peak_brightness - sdr_stats.peak_brightness,
            "shadow_detail_gain": hdr_stats.shadow_detail - sdr_stats.shadow_detail
        }
    
    def generate_telemetry_suggestions(self, stats: VideoStats, comparison: Dict) -> Dict:
        """Generate telemetry suggestions based on analysis"""
        suggestions = {
            "exposure_adjustment": 1.0,
            "contrast_enhancement": 1.0,
            "saturation_boost": 1.0,
            "highlight_preservation": False,
            "shadow_enhancement": False
        }
        
        # Exposure suggestions
        if stats.avg_brightness < 100:
            suggestions["exposure_adjustment"] = 1.2
        elif stats.avg_brightness > 150:
            suggestions["exposure_adjustment"] = 0.9
            
        # Contrast suggestions
        if comparison["dynamic_range_ratio"] > 1.5:
            suggestions["contrast_enhancement"] = 1.1
            suggestions["highlight_preservation"] = True
            
        # Saturation suggestions
        if comparison["saturation_difference"] > 20:
            suggestions["saturation_boost"] = 1.15
            
        # Shadow detail
        if stats.shadow_detail < 20:
            suggestions["shadow_enhancement"] = True
            
        return suggestions


def main():
    parser = argparse.ArgumentParser(description="Analyze HDR/SDR video pairs")
    parser.add_argument("--hdr-dir", default="data/samples/hdr", help="HDR videos directory")
    parser.add_argument("--sdr-dir", default="data/samples/sdr", help="SDR videos directory")
    parser.add_argument("--output", default="data/samples/video_analysis.json", help="Output file")
    args = parser.parse_args()
    
    analyzer = VideoAnalyzer()
    results = {}
    
    # Find video pairs
    hdr_files = list(Path(args.hdr_dir).glob("*.mp4"))
    
    for hdr_file in hdr_files:
        # Find matching SDR file
        base_name = hdr_file.stem.replace("_hdr", "")
        sdr_file = Path(args.sdr_dir) / f"{base_name}_sdr.mp4"
        
        if not sdr_file.exists():
            print(f"No SDR match for {hdr_file.name}")
            continue
            
        # Analyze both
        print(f"\nAnalyzing pair: {base_name}")
        hdr_stats = analyzer.analyze_video(str(hdr_file))
        sdr_stats = analyzer.analyze_video(str(sdr_file))
        
        # Compare
        comparison = analyzer.compare_hdr_sdr(hdr_stats, sdr_stats)
        suggestions = analyzer.generate_telemetry_suggestions(hdr_stats, comparison)
        
        # Store results
        results[base_name] = {
            "hdr_stats": hdr_stats.__dict__,
            "sdr_stats": sdr_stats.__dict__,
            "comparison": comparison,
            "telemetry_suggestions": suggestions
        }
        
        # Print summary
        print(f"\nResults for {base_name}:")
        print(f"  HDR brightness: {hdr_stats.avg_brightness:.1f}")
        print(f"  SDR brightness: {sdr_stats.avg_brightness:.1f}")
        print(f"  Dynamic range ratio: {comparison['dynamic_range_ratio']:.2f}")
        print(f"  Suggested adjustments: {suggestions}")
    
    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nAnalysis complete! Results saved to: {args.output}")


if __name__ == "__main__":
    main()