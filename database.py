"""SQLite persistence layer for Climate Intelligence."""
import os
import csv
import sqlite3
from datetime import datetime, timedelta
from climate_engine import validate_observation
from alert_engine import classify_alert
from weather_data import load_csv_observations


class ClosingConnection(sqlite3.Connection):
    """Close connections after transaction scopes so SQLite files unlock promptly."""

    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


class ClimateDatabase:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.initialize()

    def connect(self):
        con = sqlite3.connect(self.path, timeout=20, factory=ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def initialize(self):
        with self.connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                observed_at TEXT NOT NULL, station TEXT NOT NULL, city TEXT NOT NULL,
                temperature REAL NOT NULL, humidity REAL NOT NULL, wind_speed REAL NOT NULL DEFAULT 0,
                rainfall REAL NOT NULL DEFAULT 0, condition_text TEXT DEFAULT '', source TEXT DEFAULT '',
                alert_level TEXT NOT NULL, notes TEXT DEFAULT '')""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_observations_date ON observations(observed_at)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_observations_station ON observations(station)")

    def count(self, search=""):
        sql = "SELECT COUNT(*) FROM observations"
        params = []
        if search.strip():
            q = f"%{search.strip()}%"
            sql += " WHERE station LIKE ? OR city LIKE ? OR alert_level LIKE ? OR condition_text LIKE ? OR source LIKE ?"
            params = [q] * 5
        with self.connect() as con:
            return con.execute(sql, params).fetchone()[0]

    def add(self, record):
        validate_observation(record)
        with self.connect() as con:
            cur = con.execute("""INSERT INTO observations
                (observed_at,station,city,temperature,humidity,wind_speed,rainfall,condition_text,source,alert_level,notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (record["observed_at"], record["station"], record["city"], float(record["temperature"]),
                 float(record["humidity"]), float(record["wind_speed"]), float(record["rainfall"]),
                 record.get("condition_text", ""), record.get("source", "Manual entry"),
                 classify_alert(record["temperature"], record["humidity"], record["wind_speed"]), record.get("notes", "")))
            return cur.lastrowid

    def add_many(self, records):
        added = 0
        with self.connect() as con:
            for record in records:
                try:
                    validate_observation(record)
                    con.execute("""INSERT INTO observations
                        (observed_at,station,city,temperature,humidity,wind_speed,rainfall,condition_text,source,alert_level,notes)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (record["observed_at"], record["station"], record["city"], float(record["temperature"]),
                         float(record["humidity"]), float(record["wind_speed"]), float(record["rainfall"]),
                         record.get("condition_text", ""), record.get("source", "Imported dataset"),
                         classify_alert(record["temperature"], record["humidity"], record["wind_speed"]), record.get("notes", "")))
                    added += 1
                except (ValueError, TypeError, KeyError):
                    continue
        return added

    def all(self, search="", limit=None):
        params = []
        sql = "SELECT * FROM observations"
        if search.strip():
            q = f"%{search.strip()}%"
            sql += " WHERE station LIKE ? OR city LIKE ? OR alert_level LIKE ? OR condition_text LIKE ? OR source LIKE ?"
            params.extend([q] * 5)
        sql += " ORDER BY id DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        with self.connect() as con:
            return [dict(r) for r in con.execute(sql, params).fetchall()]

    def get(self, record_id):
        with self.connect() as con:
            row = con.execute("SELECT * FROM observations WHERE id=?", (int(record_id),)).fetchone()
        return dict(row) if row else None

    def update(self, record_id, record):
        validate_observation(record)
        with self.connect() as con:
            con.execute("""UPDATE observations SET observed_at=?,station=?,city=?,temperature=?,humidity=?,wind_speed=?,
                rainfall=?,condition_text=?,source=?,alert_level=?,notes=? WHERE id=?""",
                (record["observed_at"], record["station"], record["city"], float(record["temperature"]),
                 float(record["humidity"]), float(record["wind_speed"]), float(record["rainfall"]),
                 record.get("condition_text", ""), record.get("source", "Manual entry"),
                 classify_alert(record["temperature"], record["humidity"], record["wind_speed"]),
                 record.get("notes", ""), int(record_id)))

    def delete(self, record_id):
        with self.connect() as con:
            con.execute("DELETE FROM observations WHERE id=?", (int(record_id),))

    def summary(self):
        with self.connect() as con:
            row = con.execute("""SELECT COUNT(*) total, COALESCE(AVG(temperature),0) avg_temp,
                COALESCE(MAX(temperature),0) max_temp, COALESCE(MIN(temperature),0) min_temp,
                SUM(CASE WHEN alert_level='CRITICAL' THEN 1 ELSE 0 END) critical,
                SUM(CASE WHEN alert_level='WARNING' THEN 1 ELSE 0 END) warning,
                COUNT(DISTINCT station) stations FROM observations""").fetchone()
        return dict(row)

    def import_csv(self, path):
        records = load_csv_observations(path)
        return self.add_many(records), len(records)

    def export_csv(self, path):
        """Write every stored observation to a portable UTF-8 CSV report."""
        rows = self.all()
        fields = ["id", "observed_at", "station", "city", "temperature", "humidity",
                  "wind_speed", "rainfall", "condition_text", "source", "alert_level", "notes"]
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return len(rows)

    def seed_from_experiment_csvs(self, data_dir):
        """First-run bootstrap from the three 50-row climate AI-use-case datasets.
        The 24k-row general weather dataset remains available for explicit import.
        """
        if self.count() > 0:
            return 0
        preferred = ["weather_data exp 03.csv", "Exp04_IMD_50_Real_Weather_Observations.csv",
                     "Pune_Climate_50_Observations EXP 6.csv"]
        combined = []
        for filename in preferred:
            path = os.path.join(data_dir, filename)
            if os.path.isfile(path):
                try:
                    combined.extend(load_csv_observations(path))
                except (OSError, ValueError, csv.Error):
                    continue
        # If the source CSVs are not packaged, provide a small clearly-labelled fallback dataset.
        if not combined:
            now = datetime.now()
            stations = [("Pune Central","Pune",35.2,48,12),("Mumbai Coast","Mumbai",34.1,72,15),
                        ("Nagpur East","Nagpur",38.2,36,9),("Nashik Station","Nashik",36.1,51,10),
                        ("Solapur North","Solapur",39.1,32,14),("Kolhapur","Kolhapur",31.8,68,7)]
            for i,(station,city,temp,humidity,wind) in enumerate(stations):
                combined.append({"observed_at":(now-timedelta(minutes=10*(len(stations)-i))).strftime("%Y-%m-%d %H:%M:%S"),
                    "station":station,"city":city,"temperature":temp,"humidity":humidity,"wind_speed":wind,
                    "rainfall":0,"condition_text":"Demonstration sample","source":"Demo fallback","notes":"Synthetic startup sample"})
        return self.add_many(combined)
