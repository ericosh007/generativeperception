"""
GPL Telemetry Base Classes
Core telemetry data structures and interfaces
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import time


class TelemetryType(Enum):
    """Types of telemetry data"""
    AMBIENT_LIGHT = "ambient_light"
    COLOR_TEMPERATURE = "color_temperature"
    MOTION = "motion"
    SYSTEM_CPU = "system_cpu"
    SYSTEM_GPU = "system_gpu"
    SYSTEM_MEMORY = "system_memory"


@dataclass
class TelemetryData:
    """Single telemetry reading"""
    type: TelemetryType
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TelemetryFrame:
    """Collection of telemetry data for a single time point"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.data: Dict[TelemetryType, TelemetryData] = {}
        
    def add_reading(self, reading: TelemetryData):
        """Add a telemetry reading to this frame"""
        self.data[reading.type] = reading
        
    def get_value(self, telemetry_type: TelemetryType, default: float = 0.0) -> float:
        """Get value for a specific telemetry type"""
        if telemetry_type in self.data:
            return self.data[telemetry_type].value
        return default
        
    def get_latest_values(self) -> Dict[TelemetryType, float]:
        """Get all latest values as a simple dict"""
        return {t: d.value for t, d in self.data.items()}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "data": {
                t.value: {
                    "value": d.value,
                    "unit": d.unit,
                    "timestamp": d.timestamp.isoformat()
                }
                for t, d in self.data.items()
            }
        }


class TelemetrySensor:
    """Base class for telemetry sensors"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the sensor"""
        self.is_initialized = True
        
    async def read(self) -> Optional[TelemetryData]:
        """Read current value from sensor"""
        raise NotImplementedError
        
    async def shutdown(self):
        """Cleanup sensor resources"""
        self.is_initialized = False


class TelemetryCollector:
    """Base class for telemetry collection"""
    
    def __init__(self):
        self.sensors: List[TelemetrySensor] = []
        self.is_running = False
        self.current_frame: Optional[TelemetryFrame] = None
        
    def add_sensor(self, sensor: TelemetrySensor):
        """Add a sensor to the collector"""
        self.sensors.append(sensor)
        
    async def start(self):
        """Start collecting telemetry"""
        self.is_running = True
        for sensor in self.sensors:
            await sensor.initialize()
            
    async def stop(self):
        """Stop collecting telemetry"""
        self.is_running = False
        for sensor in self.sensors:
            await sensor.shutdown()
            
    async def collect_frame(self) -> TelemetryFrame:
        """Collect a single frame of telemetry data"""
        frame = TelemetryFrame()
        
        for sensor in self.sensors:
            try:
                reading = await sensor.read()
                if reading:
                    frame.add_reading(reading)
            except Exception as e:
                print(f"Error reading from sensor {sensor.name}: {e}")
                
        self.current_frame = frame
        return frame
        
    async def get_current_telemetry(self) -> Optional[TelemetryFrame]:
        """Get the most recent telemetry frame"""
        if not self.is_running:
            return None
        return self.current_frame