"""
GPL System Telemetry Collector
Collects telemetry from various sources
"""

import asyncio
from typing import List, Optional

from telemetry.base import TelemetryCollector, TelemetryFrame
from telemetry.sensors.simulated import SimulatedSensors


class SystemTelemetryCollector(TelemetryCollector):
    """Main telemetry collector that integrates all sensors"""
    
    def __init__(self, use_simulated: bool = True):
        super().__init__()
        self.use_simulated = use_simulated
        self._collection_task: Optional[asyncio.Task] = None
        self.collection_interval = 0.1  # 10Hz
        
        # Initialize with simulated sensors for demo
        if use_simulated:
            for sensor in SimulatedSensors.create_all():
                self.add_sensor(sensor)
                
    async def start(self):
        """Start continuous telemetry collection"""
        await super().start()
        
        # Start background collection task
        if not self._collection_task:
            self._collection_task = asyncio.create_task(self._collect_continuously())
            
    async def stop(self):
        """Stop telemetry collection"""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None
            
        await super().stop()
        
    async def _collect_continuously(self):
        """Background task to collect telemetry continuously"""
        while self.is_running:
            try:
                await self.collect_frame()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in telemetry collection: {e}")
                await asyncio.sleep(self.collection_interval)