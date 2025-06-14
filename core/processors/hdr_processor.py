"""
GPL HDR Processor
Advanced HDR processing with telemetry-driven adjustments
Optimized for Apple M4 Pro with Metal acceleration
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
import time
from scipy.interpolate import interp1d

from config.settings import settings, HDR_PRESETS, TELEMETRY_HDR_MAPPINGS
from telemetry.base import TelemetryFrame, TelemetryType


@dataclass
class HDRParameters:
    """Dynamic HDR processing parameters"""
    exposure: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.1
    clahe_clip: float = 3.0
    clahe_grid: Tuple[int, int] = (8, 8)
    sharpening: float = 0.6
    highlights: float = 0.0
    shadows: float = 0.0
    white_balance: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    tone_curve: str = "s_curve"
    denoise_strength: int = 5
    
    def interpolate_from_telemetry(self, telemetry: Dict[TelemetryType, Any]):
        """Update parameters based on telemetry data"""
        # Ambient light adjustments
        if TelemetryType.AMBIENT_LIGHT in telemetry:
            lux = telemetry[TelemetryType.AMBIENT_LIGHT]
            mapping = TELEMETRY_HDR_MAPPINGS["ambient_light"]
            
            # Interpolate between defined points
            lux_points = sorted(mapping.keys())
            if lux <= lux_points[0]:
                params = mapping[lux_points[0]]
            elif lux >= lux_points[-1]:
                params = mapping[lux_points[-1]]
            else:
                # Linear interpolation
                for i in range(len(lux_points) - 1):
                    if lux_points[i] <= lux <= lux_points[i + 1]:
                        t = (lux - lux_points[i]) / (lux_points[i + 1] - lux_points[i])
                        p1, p2 = mapping[lux_points[i]], mapping[lux_points[i + 1]]
                        self.exposure = p1["exposure"] * (1 - t) + p2["exposure"] * t
                        self.contrast = p1["contrast"] * (1 - t) + p2["contrast"] * t
                        break
        
        # Motion adjustments
        if TelemetryType.MOTION in telemetry:
            motion = telemetry[TelemetryType.MOTION]
            motion_map = TELEMETRY_HDR_MAPPINGS["motion_level"]
            
            # Find closest motion level
            levels = sorted(motion_map.keys())
            closest = min(levels, key=lambda x: abs(x - motion))
            self.sharpening = motion_map[closest]["sharpening"]
        
        # Color temperature adjustments
        if TelemetryType.COLOR_TEMPERATURE in telemetry:
            kelvin = telemetry[TelemetryType.COLOR_TEMPERATURE]
            temp_map = TELEMETRY_HDR_MAPPINGS["color_temperature"]
            
            # Interpolate white balance
            temps = sorted(temp_map.keys())
            if kelvin <= temps[0]:
                wb = temp_map[temps[0]]
            elif kelvin >= temps[-1]:
                wb = temp_map[temps[-1]]
            else:
                # Interpolate
                for i in range(len(temps) - 1):
                    if temps[i] <= kelvin <= temps[i + 1]:
                        t = (kelvin - temps[i]) / (temps[i + 1] - temps[i])
                        w1, w2 = temp_map[temps[i]], temp_map[temps[i + 1]]
                        r = w1["r_gain"] * (1 - t) + w2["r_gain"] * t
                        b = w1["b_gain"] * (1 - t) + w2["b_gain"] * t
                        self.white_balance = (r, 1.0, b)
                        break


class HDRProcessor:
    """Advanced HDR video processor with telemetry integration"""
    
    def __init__(self, preset: str = "balanced"):
        self.preset = preset
        self.params = HDRParameters()
        self._update_from_preset(preset)
        
        # Create lookup tables for performance
        self._create_luts()
        
        # Performance tracking
        self.frame_count = 0
        self.total_time = 0.0
        
    def _update_from_preset(self, preset: str):
        """Update parameters from preset"""
        if preset in HDR_PRESETS:
            p = HDR_PRESETS[preset]
            self.params.clahe_clip = p["clahe_clip"]
            self.params.clahe_grid = p["clahe_grid"]
            self.params.saturation = p["saturation_boost"]
            self.params.sharpening = p["sharpening"]
            self.params.tone_curve = p["tone_curve"]
            if p.get("denoise"):
                self.params.denoise_strength = p["denoise_strength"]
    
    def _create_luts(self):
        """Pre-calculate lookup tables for performance"""
        # Gamma decode/encode LUTs
        self.gamma_decode = np.array(
            [(i / 255.0) ** 2.2 * 255 for i in range(256)], 
            dtype=np.uint8
        )
        self.gamma_encode = np.array(
            [(i / 255.0) ** (1 / 2.2) * 255 for i in range(256)], 
            dtype=np.uint8
        )
        
        # S-curve LUT
        x = np.linspace(0, 1, 256)
        s = 1 / (1 + np.exp(-12 * (x - 0.5)))  # Steeper S-curve
        self.s_curve_lut = (s * 255).astype(np.uint8)
        
        # Highlight compression LUT
        self.highlight_lut = self._create_highlight_lut()
    
    def _create_highlight_lut(self, knee_point: float = 0.7) -> np.ndarray:
        """Create highlight compression LUT with knee"""
        x = np.linspace(0, 1, 256)
        y = np.zeros_like(x)
        
        # Linear up to knee point
        mask = x <= knee_point
        y[mask] = x[mask]
        
        # Compressed above knee (Reinhard-style)
        mask = x > knee_point
        y[mask] = knee_point + (x[mask] - knee_point) / (1 + (x[mask] - knee_point))
        
        return (y * 255).astype(np.uint8)
    
    def process_frame(self, 
                     frame: np.ndarray, 
                     telemetry: Optional[TelemetryFrame] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process a single frame with HDR enhancement
        
        Args:
            frame: Input frame (BGR, uint8)
            telemetry: Current telemetry data
            
        Returns:
            Tuple of (processed_frame, metrics)
        """
        start_time = time.perf_counter()
        
        # Update parameters from telemetry
        if telemetry:
            telemetry_values = telemetry.get_latest_values()
            self.params.interpolate_from_telemetry(telemetry_values)
        
        # 1. Gamma decode to linear space
        linear = cv2.LUT(frame, self.gamma_decode)
        
        # 2. Apply white balance in linear space
        if self.params.white_balance != (1.0, 1.0, 1.0):
            b, g, r = cv2.split(linear)
            b = np.clip(b * self.params.white_balance[2], 0, 255).astype(np.uint8)
            r = np.clip(r * self.params.white_balance[0], 0, 255).astype(np.uint8)
            linear = cv2.merge([b, g, r])
        
        # 3. Convert to LAB for CLAHE
        lab = cv2.cvtColor(linear, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # 4. Advanced CLAHE with telemetry-based parameters
        clahe = cv2.createCLAHE(
            clipLimit=self.params.clahe_clip,
            tileGridSize=self.params.clahe_grid
        )
        l = clahe.apply(l)
        
        # 5. Apply exposure adjustment
        if self.params.exposure != 1.0:
            l = np.clip(l * self.params.exposure, 0, 255).astype(np.uint8)
        
        # 6. Merge and convert back
        lab = cv2.merge([l, a, b])
        bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 7. Apply tone curve
        if self.params.tone_curve == "s_curve":
            bgr = cv2.LUT(bgr, self.s_curve_lut)
        elif self.params.tone_curve == "adaptive":
            # Adaptive tone curve based on histogram
            bgr = self._apply_adaptive_tone_curve(bgr)
        
        # 8. Saturation boost in HSV
        if self.params.saturation != 1.0:
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] *= self.params.saturation
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            bgr = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        
        # 9. Detail enhancement (edge-aware)
        if self.params.sharpening > 0:
            bgr = self._enhance_details(bgr, self.params.sharpening)
        
        # 10. Highlight/shadow adjustment
        if self.params.highlights != 0 or self.params.shadows != 0:
            bgr = self._adjust_highlights_shadows(bgr)
        
        # 11. Optional denoise
        if self.params.denoise_strength > 0:
            bgr = cv2.fastNlMeansDenoisingColored(
                bgr, None, 
                self.params.denoise_strength,
                self.params.denoise_strength,
                7, 21
            )
        
        # 12. Gamma re-encode
        final = cv2.LUT(bgr, self.gamma_encode)
        
        # Calculate metrics
        process_time = (time.perf_counter() - start_time) * 1000  # ms
        self.frame_count += 1
        self.total_time += process_time
        
        metrics = {
            "process_time_ms": process_time,
            "avg_time_ms": self.total_time / self.frame_count,
            "params": {
                "exposure": self.params.exposure,
                "contrast": self.params.contrast,
                "saturation": self.params.saturation,
                "sharpening": self.params.sharpening
            }
        }
        
        return final, metrics
    
    def _enhance_details(self, img: np.ndarray, strength: float) -> np.ndarray:
        """Edge-aware detail enhancement using guided filter"""
        # Simple unsharp mask for now (can be replaced with guided filter)
        gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)
        enhanced = cv2.addWeighted(img, 1.0 + strength, gaussian, -strength, 0)
        return enhanced
    
    def _apply_adaptive_tone_curve(self, img: np.ndarray) -> np.ndarray:
        """Apply adaptive tone curve based on image histogram"""
        # Convert to grayscale for histogram
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()
        
        # Calculate cumulative distribution
        cdf = hist.cumsum()
        
        # Create adaptive curve
        curve = (cdf * 255).astype(np.uint8)
        
        # Apply to each channel
        return cv2.LUT(img, curve)
    
    def _adjust_highlights_shadows(self, img: np.ndarray) -> np.ndarray:
        """Adjust highlights and shadows separately"""
        # Convert to float
        img_f = img.astype(np.float32) / 255.0
        
        # Create masks
        lum = cv2.cvtColor(img_f, cv2.COLOR_BGR2GRAY)
        highlight_mask = np.clip((lum - 0.5) * 2, 0, 1)
        shadow_mask = np.clip((0.5 - lum) * 2, 0, 1)
        
        # Apply adjustments
        if self.params.highlights != 0:
            adjustment = 1 + self.params.highlights * highlight_mask[:, :, np.newaxis]
            img_f *= adjustment
        
        if self.params.shadows != 0:
            adjustment = 1 + self.params.shadows * shadow_mask[:, :, np.newaxis]
            img_f *= adjustment
        
        # Convert back
        return np.clip(img_f * 255, 0, 255).astype(np.uint8)