"""
GPL Configuration Settings
Centralized configuration management with environment variable support
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List, Dict, Optional
from enum import Enum


class ProcessingMode(str, Enum):
    """HDR processing modes"""
    REALTIME = "realtime"
    QUALITY = "quality"
    ADAPTIVE = "adaptive"


class TelemetrySource(str, Enum):
    """Available telemetry sources"""
    SYSTEM = "system"
    SENSOR = "sensor"
    SIMULATED = "simulated"
    NETWORK = "network"


class Settings(BaseSettings):
    """GPL Global Settings"""
    
    # Application
    app_name: str = "Generative Perception Layers"
    app_version: str = "1.0.0"
    debug: bool = Field(False, env="GPL_DEBUG")
    
    # Processing Engine
    processing_mode: ProcessingMode = Field(ProcessingMode.ADAPTIVE, env="GPL_MODE")
    target_fps: int = Field(30, env="GPL_TARGET_FPS")
    max_resolution: tuple = (3840, 2160)  # 4K max
    enable_gpu: bool = Field(True, env="GPL_USE_GPU")
    enable_neural_engine: bool = Field(True, env="GPL_USE_NEURAL")
    
    # HDR Parameters
    hdr_base_algorithm: str = Field("advanced_clahe", env="GPL_HDR_ALGO")
    hdr_quality_preset: str = Field("balanced", env="GPL_HDR_PRESET")
    dynamic_range_nits: int = Field(1000, env="GPL_HDR_NITS")
    
    # Telemetry Configuration
    telemetry_sources: List[TelemetrySource] = Field(
        [TelemetrySource.SYSTEM, TelemetrySource.SIMULATED],
        env="GPL_TELEMETRY_SOURCES"
    )
    telemetry_update_rate: float = Field(10.0, env="GPL_TELEMETRY_HZ")  # Hz
    telemetry_buffer_size: int = Field(1000, env="GPL_TELEMETRY_BUFFER")
    
    # Sensor Defaults
    ambient_light_range: tuple = (0, 10000)  # lux
    color_temp_range: tuple = (2000, 8000)   # kelvin
    motion_threshold: float = Field(0.3, env="GPL_MOTION_THRESHOLD")
    
    # Web Server
    host: str = Field("0.0.0.0", env="GPL_HOST")
    port: int = Field(8000, env="GPL_PORT")
    cors_origins: List[str] = Field(["*"], env="GPL_CORS_ORIGINS")
    
    # Streaming
    stream_protocol: str = Field("webrtc", env="GPL_STREAM_PROTOCOL")
    stream_bitrate: int = Field(8000000, env="GPL_STREAM_BITRATE")  # 8 Mbps
    stream_codec: str = Field("h264", env="GPL_STREAM_CODEC")
    low_latency_mode: bool = Field(True, env="GPL_LOW_LATENCY")
    
    # Redis Cache
    redis_url: str = Field("redis://localhost:6379", env="GPL_REDIS_URL")
    cache_ttl: int = Field(3600, env="GPL_CACHE_TTL")
    
    # Monitoring
    enable_metrics: bool = Field(True, env="GPL_METRICS")
    metrics_port: int = Field(9090, env="GPL_METRICS_PORT")
    log_level: str = Field("INFO", env="GPL_LOG_LEVEL")
    
    # Paths
    data_dir: str = Field("./data", env="GPL_DATA_DIR")
    model_dir: str = Field("./models", env="GPL_MODEL_DIR")
    output_dir: str = Field("./data/output", env="GPL_OUTPUT_DIR")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# HDR Algorithm Presets
HDR_PRESETS = {
    "performance": {
        "clahe_clip": 2.0,
        "clahe_grid": (4, 4),
        "saturation_boost": 1.05,
        "sharpening": 0.3,
        "tone_curve": "linear",
        "denoise": False
    },
    "balanced": {
        "clahe_clip": 3.0,
        "clahe_grid": (8, 8),
        "saturation_boost": 1.10,
        "sharpening": 0.6,
        "tone_curve": "s_curve",
        "denoise": True,
        "denoise_strength": 5
    },
    "quality": {
        "clahe_clip": 4.0,
        "clahe_grid": (16, 16),
        "saturation_boost": 1.15,
        "sharpening": 0.8,
        "tone_curve": "adaptive",
        "denoise": True,
        "denoise_strength": 10,
        "detail_enhancement": True
    }
}


# Telemetry-based HDR Mappings
TELEMETRY_HDR_MAPPINGS = {
    "ambient_light": {
        # lux -> HDR adjustment factor
        0: {"exposure": 1.8, "contrast": 1.2},      # Dark
        100: {"exposure": 1.4, "contrast": 1.1},    # Dim indoor
        500: {"exposure": 1.2, "contrast": 1.0},    # Normal indoor
        1000: {"exposure": 1.0, "contrast": 0.95},  # Bright indoor
        10000: {"exposure": 0.8, "contrast": 0.9},  # Daylight
    },
    "motion_level": {
        # motion -> processing adjustments
        0.0: {"sharpening": 0.8, "temporal_denoise": True},   # Static
        0.3: {"sharpening": 0.6, "temporal_denoise": True},   # Slow
        0.6: {"sharpening": 0.4, "temporal_denoise": False},  # Medium
        1.0: {"sharpening": 0.2, "temporal_denoise": False},  # Fast
    },
    "color_temperature": {
        # kelvin -> white balance shift
        2000: {"r_gain": 1.3, "b_gain": 0.7},   # Candle
        3000: {"r_gain": 1.1, "b_gain": 0.85},  # Tungsten
        5000: {"r_gain": 1.0, "b_gain": 1.0},   # Daylight
        7000: {"r_gain": 0.9, "b_gain": 1.15},  # Cloudy
    }
}