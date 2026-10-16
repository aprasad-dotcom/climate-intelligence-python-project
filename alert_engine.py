"""Alert generation module (Experiment 05: separate climate alert logic)."""
WARNING_C = 37.0
CRITICAL_C = 40.0


def classify_alert(temperature, humidity=50, wind_speed=0):
    """Educational demonstration thresholds, not official IMD heatwave criteria."""
    temp = float(temperature)
    if temp >= CRITICAL_C:
        return "CRITICAL"
    if temp >= WARNING_C:
        return "WARNING"
    return "NORMAL"


def monitor_conditions(record):
    """Evaluate all three sensor fields during a concurrent monitoring pass.

    Humidity and wind bands are descriptive classroom signals; they do not alter
    the temperature-only NORMAL/WARNING/CRITICAL category.
    """
    temperature = float(record["temperature"])
    humidity = float(record.get("humidity", 50))
    wind_speed = float(record.get("wind_speed", 0))
    return {"alert_level": classify_alert(temperature, humidity, wind_speed),
            "humidity_status": "HIGH" if humidity >= 70 else "LOW" if humidity < 30 else "MODERATE",
            "wind_status": "ELEVATED" if wind_speed >= 20 else "MODERATE"}


def build_alert_message(record):
    """Create a concise alert string for an observation dictionary."""
    level = classify_alert(record.get("temperature", 0), record.get("humidity", 50), record.get("wind_speed", 0))
    temperature = float(record.get("temperature", 0))
    station = str(record.get("station", "Unknown station")).strip() or "Unknown station"
    if level == "CRITICAL":
        detail = "Critical demonstration threshold reached. Review the station reading immediately."
    elif level == "WARNING":
        detail = "Warning demonstration threshold reached. Continue monitoring incoming readings."
    else:
        detail = "Reading is below the configured demonstration warning threshold."
    return {"level": level, "title": f"{level}: {station}",
            "message": f"{station} recorded {temperature:.1f}°C. {detail}"}
