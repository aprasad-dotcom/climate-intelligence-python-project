"""Weather-data collection and CSV normalization module (Experiment 05)."""
import csv
import math
from datetime import datetime, timezone
from climate_engine import ClimateObservation, normalize_text, validate_observation


class ImportedClimateObservation(ClimateObservation):
    """Experiment 03: imported rows reuse the climate base model and normalize labels."""

    def __init__(self, record):
        super().__init__(record["station"], record["city"], record["temperature"],
                         record["humidity"], record["wind_speed"], record["rainfall"],
                         record["observed_at"], record["condition_text"],
                         record["source"], record["notes"])

    def to_dict(self):
        result = super().to_dict()
        result["condition_text"] = normalize_text(result["condition_text"]).capitalize()
        return result


def _row_lookup(row):
    return {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items() if k is not None}


def _pick(row, names, default=None):
    for name in names:
        key = name.lower().replace(" ", "_")
        value = row.get(key)
        if value is not None and str(value).strip() not in ("", "nan", "None", "null"):
            return value
    return default


def _float(value, default=None):
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def _date_value(value):
    value = normalize_text(value)
    if not value:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Experiment 05 weather API data uses Unix epoch seconds.
    try:
        n = float(value)
        if n > 1_000_000_000:
            return datetime.fromtimestamp(n, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        pass
    return value[:64]


def load_csv_observations(path):
    """Normalize the differently named columns in the supplied experiment CSVs."""
    output = []
    with open(path, "r", newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("This CSV does not contain a header row.")
        for line_number, raw in enumerate(reader, start=2):
            row = _row_lookup(raw)
            temp = _pick(row, ["temperature_c", "temperature_celsius", "temperature", "temp_c", "maximum_temperature", "feels_like_celsius"])
            if temp is None:
                continue
            temp_n = _float(temp)
            if temp_n is None:
                continue
            station = _pick(row, ["station_id", "station", "station_name", "location", "city"], "Weather API sample")
            city = _pick(row, ["city", "region", "state", "station"], "Weather API dataset")
            humidity = _float(_pick(row, ["humidity_percent", "humidity", "relative_humidity"], 50), 50)
            wind = _float(_pick(row, ["wind_speed", "wind_kph", "wind_speed_kph", "wind_mph", "wind_speed_km_h"], 0), 0)
            if "wind_mph" in row and "wind_kph" not in row and "wind_speed" not in row:
                wind *= 1.60934
            rain = _float(_pick(row, ["rainfall_mm", "rainfall", "precip_mm", "precipitation_mm"], 0), 0)
            date = _pick(row, ["date_time_utc", "date", "timestamp", "last_updated", "last_updated_epoch", "datetime", "time"], None)
            condition = _pick(row, ["condition", "condition_text", "weather", "observation_type"], "Imported observation")
            record = {"observed_at": _date_value(date), "station": normalize_text(station, "Unknown station"),
                      "city": normalize_text(city, "Unknown city"), "temperature": temp_n,
                      "humidity": humidity, "wind_speed": wind, "rainfall": rain,
                      "condition_text": normalize_text(condition, "Imported observation"),
                      "source": "Imported dataset", "notes": f"CSV row {line_number}"}
            try:
                record = ImportedClimateObservation(record).to_dict()
                validate_observation(record)
                output.append(record)
            except ValueError:
                continue
    return output
