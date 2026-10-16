"""Climate analysis logic: OOP, inheritance, abstraction and functional programming."""
import math
from abc import ABC, abstractmethod
from functools import reduce
from datetime import datetime
from alert_engine import classify_alert


def normalize_text(value, fallback=""):
    """Experiment 03: trim, normalize whitespace and validate text labels."""
    text = " ".join(str(value if value is not None else "").strip().split())
    return text or fallback


def celsius_to_fahrenheit(value):
    return float(value) * 9 / 5 + 32


def validate_observation(record):
    required = ("observed_at", "station", "city", "temperature", "humidity", "wind_speed", "rainfall")
    for key in required:
        if key not in record or str(record[key]).strip() == "":
            raise ValueError(f"Missing required field: {key.replace('_', ' ')}")
    try:
        temperature = float(record["temperature"]); humidity = float(record["humidity"])
        wind = float(record["wind_speed"]); rainfall = float(record["rainfall"])
    except (ValueError, TypeError) as exc:
        raise ValueError("Temperature, humidity, wind speed and rainfall must be numeric.") from exc
    if not math.isfinite(temperature) or not -20 <= temperature <= 60:
        raise ValueError("Temperature must be a finite value between -20°C and 60°C.")
    if not math.isfinite(humidity) or not 0 <= humidity <= 100:
        raise ValueError("Humidity must be between 0% and 100%.")
    if not math.isfinite(wind) or wind < 0:
        raise ValueError("Wind speed cannot be negative.")
    if not math.isfinite(rainfall) or rainfall < 0:
        raise ValueError("Rainfall cannot be negative.")
    if not normalize_text(record["station"]):
        raise ValueError("Station is required.")
    return True


class ClimateObservation:
    """Experiments 01–02: class, object, constructor and climate data model."""
    def __init__(self, station="Unknown station", city="Unknown city", temperature=0, humidity=50, wind_speed=0, rainfall=0,
                 observed_at=None, condition_text="", source="Manual entry", notes=""):
        self.station = normalize_text(station, "Unknown station")
        self.city = normalize_text(city, "Unknown city")
        self.temperature = temperature
        self.humidity = float(humidity)
        self.wind_speed = float(wind_speed or 0)
        self.rainfall = float(rainfall or 0)
        self.observed_at = normalize_text(observed_at, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.condition_text = normalize_text(condition_text, "Not specified")
        self.source = normalize_text(source, "Manual entry")
        self.notes = normalize_text(notes)

    def to_dict(self):
        return {"observed_at": self.observed_at, "station": self.station, "city": self.city,
                "temperature": self.temperature, "humidity": self.humidity, "wind_speed": self.wind_speed,
                "rainfall": self.rainfall, "condition_text": self.condition_text,
                "source": self.source, "notes": self.notes}

    @property
    def temperature(self):
        """Encapsulated temperature reading exposed through a public property."""
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        value = float(value)
        if not math.isfinite(value) or not -20 <= value <= 60:
            raise ValueError("Temperature must be a finite value between -20°C and 60°C.")
        self._temperature = value

    @staticmethod
    def celsius_to_fahrenheit(value):
        """Experiment 01: a class-level utility that does not need an instance."""
        return celsius_to_fahrenheit(value)

    @classmethod
    def from_mapping(cls, values):
        """Experiment 01: alternate constructor for imported/SQLite mappings."""
        return cls(values.get("station", "Unknown station"), values.get("city", "Unknown city"),
                   values.get("temperature", 0), values.get("humidity", 50),
                   values.get("wind_speed", 0), values.get("rainfall", 0),
                   values.get("observed_at"), values.get("condition_text", ""),
                   values.get("source", "Manual entry"), values.get("notes", ""))

    def summary(self):
        """Experiment 01: instance method describing this observation."""
        return f"{self.station} ({self.city}) recorded {self.temperature:.1f}°C"


class AnalyzerBase(ABC):
    """Experiment 04: abstract interface for a climate analysis operation."""
    @abstractmethod
    def analyze(self, observations):
        raise NotImplementedError


class HeatwaveAnalyzer(AnalyzerBase):
    """Experiments 03–04: inheritance, method implementation and polymorphic analysis."""
    def analyze(self, observations):
        # Collections + functional programming from Experiment 06.
        temperatures = list(map(lambda r: float(r["temperature"] if isinstance(r, dict) else r.temperature), observations))
        # Experiment 06 asks for readings needing heatwave monitoring at >=40°C.
        hot = list(filter(lambda temp: temp >= 40.0, temperatures))
        total = reduce(lambda a, b: a + b, temperatures, 0.0)
        square_first = (lambda value: value * value)(temperatures[0]) if temperatures else None
        return {"count": len(temperatures), "average": total / len(temperatures) if temperatures else 0.0,
                "minimum": min(temperatures) if temperatures else None,
                "maximum": max(temperatures) if temperatures else None,
                "total": total, "square_first": square_first, "hot_count": len(hot), "hot_values": hot,
                "fahrenheit": list(map(celsius_to_fahrenheit, temperatures)),
                "alert_levels": {classify_alert(temp) for temp in temperatures}}


class RainfallAnalyzer(AnalyzerBase):
    """A second implementation of the analyzer contract for rainfall observations."""

    def analyze(self, observations):
        rainfall = [float(row.get("rainfall", 0) if isinstance(row, dict) else row.rainfall)
                    for row in observations]
        total = reduce(lambda left, right: left + right, rainfall, 0.0)
        wet_readings = list(filter(lambda amount: amount > 0, rainfall))
        return {"count": len(rainfall), "total_rainfall": total,
                "average_rainfall": total / len(rainfall) if rainfall else 0.0,
                "wet_readings": len(wet_readings)}
