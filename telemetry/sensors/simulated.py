"""
GPL Simulated Sensors
Provides simulated telemetry data for demos
"""

import asyncio
import math
import time
import random
from typing import Optional

from telemetry.base import TelemetrySensor, TelemetryData, TelemetryType


class SimulatedLightSensor(TelemetrySensor):
    """Simulates ambient light sensor with day/night cycles"""
    
    def __init__(self):
        super().__init__("simulated_light")
        self.start_time = time.time()
        self.cycle_duration = 120  # 2 minute day/night cycle for demo
        
    async def read(self) -> Optional[TelemetryData]:
        """Simulate ambient light that cycles through day/night"""
        elapsed = time.time() - self.start_time
        cycle_position = (elapsed % self.cycle_duration) / self.cycle_duration
        
        # Simulate sunrise -> noon -> sunset -> night
        if cycle_position < 0.25:  # Dawn
            lux = 100 + (900 * (cycle_position * 4))
        elif cycle_position < 0.5:  # Morning to noon
            lux = 1000 + (4000 * ((cycle_position - 0.25) * 4))
        elif cycle_position < 0.75:  # Afternoon to dusk
            lux = 5000 - (4000 * ((cycle_position - 0.5) * 4))
        else:  # Night
            lux = 1000 - (900 * ((cycle_position - 0.75) * 4))
            
        # Add some noise
        lux += random.uniform(-50, 50)
        lux = max(50, min(5000, lux))
        
        return TelemetryData(
            type=TelemetryType.AMBIENT_LIGHT,
            value=lux,
            unit="lux"
        )


class SimulatedColorTempSensor(TelemetrySensor):
    """Simulates color temperature sensor correlating with light"""
    
    def __init__(self):
        super().__init__("simulated_color_temp")
        self.start_time = time.time()
        self.cycle_duration = 120
        
    async def read(self) -> Optional[TelemetryData]:
        """Simulate color temperature that changes with time of day"""
        elapsed = time.time() - self.start_time
        cycle_position = (elapsed % self.cycle_duration) / self.cycle_duration
        
        # Morning: warm -> Day: neutral -> Evening: warm
        if cycle_position < 0.3:  # Morning
            kelvin = 3000 + (2000 * (cycle_position / 0.3))
        elif cycle_position < 0.7:  # Day
            kelvin = 5000 + (1000 * math.sin((cycle_position - 0.3) * 2.5 * math.pi))
        else:  # Evening
            kelvin = 5000 - (2000 * ((cycle_position - 0.7) / 0.3))
            
        kelvin += random.uniform(-100, 100)
        kelvin = max(2700, min(6500, kelvin))
        
        return TelemetryData(
            type=TelemetryType.COLOR_TEMPERATURE,
            value=kelvin,
            unit="kelvin"
        )


class SimulatedMotionSensor(TelemetrySensor):
    """Simulates motion detection with varying activity levels"""
    
    def __init__(self):
        super().__init__("simulated_motion")
        self.motion_level = 0.3
        self.target_motion = 0.3
        self.last_change = time.time()
        
    async def read(self) -> Optional[TelemetryData]:
        """Simulate motion that changes periodically"""
        current_time = time.time()
        
        # Change target motion every 10-20 seconds
        if current_time - self.last_change > random.uniform(10, 20):
            self.target_motion = random.choice([0.1, 0.3, 0.5, 0.7, 0.9])
            self.last_change = current_time
            
        # Smooth transition to target
        self.motion_level += (self.target_motion - self.motion_level) * 0.1
        
        # Add noise
        motion = self.motion_level + random.uniform(-0.05, 0.05)
        motion = max(0.0, min(1.0, motion))
        
        return TelemetryData(
            type=TelemetryType.MOTION,
            value=motion,
            unit="normalized"
        )


class SimulatedSensors:
    """Factory for creating simulated sensors"""
    
    @staticmethod
    def create_all():
        """Create all simulated sensors"""
        return [
            SimulatedLightSensor(),
            SimulatedColorTempSensor(),
            SimulatedMotionSensor()
        ]
        
    @staticmethod
    def create_basic():
        """Create basic set of sensors"""
        return [
            SimulatedLightSensor(),
            SimulatedMotionSensor()
        ]