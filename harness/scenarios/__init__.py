"""
Registry of PMS degradation scenarios for simulation harness.
"""

from .base import BaseScenario, ScenarioStep
from .overstrain import OverstrainScenario
from .sensor_glitch import SensorGlitchScenario
from .thermal_runaway import ThermalRunawayScenario
from .tool_wear import ToolWearScenario

SCENARIO_REGISTRY: dict[str, type[BaseScenario]] = {
    "thermal": ThermalRunawayScenario,
    "thermal_runaway": ThermalRunawayScenario,
    "overstrain": OverstrainScenario,
    "tool_wear": ToolWearScenario,
    "sensor_glitch": SensorGlitchScenario,
}

__all__ = [
    "BaseScenario",
    "ScenarioStep",
    "ThermalRunawayScenario",
    "OverstrainScenario",
    "ToolWearScenario",
    "SensorGlitchScenario",
    "SCENARIO_REGISTRY",
]
