import csv
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_ROOT = os.path.join(ROOT, "work", "test-tmp")
os.makedirs(TEMP_ROOT, exist_ok=True)
tempfile.tempdir = TEMP_ROOT
sys.path.insert(0, ROOT)

from alert_engine import classify_alert, build_alert_message, monitor_conditions
from climate_engine import ClimateObservation, HeatwaveAnalyzer, RainfallAnalyzer, celsius_to_fahrenheit, validate_observation
from weather_data import load_csv_observations
from database import ClimateDatabase
from experiment_support import StudentMarks, FinalStudentResult


class ClimateEngineTests(unittest.TestCase):
    def test_alert_threshold_categories(self):
        self.assertEqual(classify_alert(36.9), "NORMAL")
        self.assertEqual(classify_alert(37.0), "WARNING")
        self.assertEqual(classify_alert(40.0), "CRITICAL")

    def test_observation_constructor_and_validation(self):
        default_item = ClimateObservation()
        self.assertEqual(default_item.station, "Unknown station")
        self.assertEqual(default_item.humidity, 50)
        item = ClimateObservation("  Pune   Central ", " Pune ", 38, 45, 10, 0)
        record = item.to_dict()
        self.assertEqual(record["station"], "Pune Central")
        self.assertTrue(validate_observation(record))

    def test_invalid_humidity_rejected(self):
        item = ClimateObservation("Pune", "Pune", 35, 101, 10, 0).to_dict()
        with self.assertRaises(ValueError):
            validate_observation(item)

    def test_functional_analysis(self):
        records = [{"temperature": 30}, {"temperature": 38}, {"temperature": 41}]
        result = HeatwaveAnalyzer().analyze(records)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["hot_count"], 1)
        self.assertEqual(result["hot_values"], [41.0])
        self.assertEqual(result["total"], 109)
        self.assertEqual(result["square_first"], 900)
        self.assertAlmostEqual(result["average"], 109 / 3)
        self.assertAlmostEqual(celsius_to_fahrenheit(0), 32)

    def test_polymorphic_analyzers_share_one_interface(self):
        rows = [{"temperature": 41, "rainfall": 2}, {"temperature": 30, "rainfall": 0}]
        heat = HeatwaveAnalyzer().analyze(rows)
        rain = RainfallAnalyzer().analyze(rows)
        self.assertEqual(heat["hot_values"], [41.0])
        self.assertEqual(rain["total_rainfall"], 2.0)
        self.assertEqual(rain["wet_readings"], 1)

    def test_alert_message(self):
        result = build_alert_message({"station": "Nagpur", "temperature": 41})
        self.assertEqual(result["level"], "CRITICAL")
        self.assertIn("Nagpur", result["message"])

    def test_concurrent_sensor_monitor_checks_temperature_humidity_and_wind(self):
        result = monitor_conditions({"temperature": 38, "humidity": 75, "wind_speed": 22})
        self.assertEqual(result, {"alert_level": "WARNING", "humidity_status": "HIGH", "wind_status": "ELEVATED"})

    def test_csv_normalizer_supports_exp03_and_exp06(self):
        data_dir = os.path.join(ROOT, "data", "raw")
        for name in ("weather_data exp 03.csv", "Pune_Climate_50_Observations EXP 6.csv", "Exp04_IMD_50_Real_Weather_Observations.csv"):
            with self.subTest(dataset=name):
                rows = load_csv_observations(os.path.join(data_dir, name))
                self.assertEqual(len(rows), 50)
                self.assertIn("temperature", rows[0])

    def test_large_experiment_05_weather_dataset(self):
        data_dir = os.path.join(ROOT, "data", "raw")
        rows = load_csv_observations(os.path.join(data_dir, "Weather data (EXP5).csv"))
        self.assertGreater(len(rows), 20000)
        self.assertIn("temperature", rows[0])
        self.assertIn("humidity", rows[0])
        self.assertIn("wind_speed", rows[0])

    def test_sqlite_bootstrap_uses_three_climate_datasets(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ClimateDatabase(os.path.join(folder, "bootstrap.db"))
            added = db.seed_from_experiment_csvs(os.path.join(ROOT, "data", "raw"))
            self.assertEqual(added, 150)
            self.assertEqual(db.count(), 150)

    def test_sqlite_crud(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ClimateDatabase(os.path.join(folder, "test.db"))
            item = ClimateObservation("Pune", "Pune", 38, 55, 10, 0).to_dict()
            rid = db.add(item)
            self.assertEqual(db.get(rid)["alert_level"], "WARNING")
            item["temperature"] = 41
            db.update(rid, item)
            self.assertEqual(db.get(rid)["alert_level"], "CRITICAL")
            self.assertEqual(db.summary()["total"], 1)
            db.delete(rid)
            self.assertEqual(db.count(), 0)

    def test_csv_import_and_export_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            db = ClimateDatabase(os.path.join(folder, "roundtrip.db"))
            source = os.path.join(ROOT, "data", "raw", "Pune_Climate_50_Observations EXP 6.csv")
            added, parsed = db.import_csv(source)
            self.assertEqual((added, parsed), (50, 50))
            target = os.path.join(folder, "report.csv")
            self.assertEqual(db.export_csv(target), 50)
            with open(target, newline="", encoding="utf-8-sig") as handle:
                self.assertEqual(sum(1 for _ in csv.DictReader(handle)), 50)

    def test_experiment_01_getter_setter_and_static_class_methods(self):
        student = StudentMarks("S001", " sample   student ", [80, 85, 90, 95])
        self.assertEqual(student.get_marks(), (80, 85, 90, 95))
        self.assertEqual(student.percentage(), 87.5)
        student.set_marks([70, 75, 80, 85])
        self.assertEqual(student.total(), 310)
        observation = ClimateObservation("Pune", "Pune", 40, 60)
        self.assertEqual(observation.summary(), "Pune (Pune) recorded 40.0°C")
        self.assertAlmostEqual(ClimateObservation.celsius_to_fahrenheit(0), 32)

    def test_experiment_03_multilevel_inheritance_result(self):
        result = FinalStudentResult("S101", "Sample Student", [80, 90, 70], 95).report()
        self.assertEqual(result["total"], 335)
        self.assertEqual(result["average"], 83.75)

    def test_imported_observations_use_normalized_subclass(self):
        from weather_data import ImportedClimateObservation
        record = ClimateObservation("  pune   central ", " PUNE ", 35, 50).to_dict()
        imported = ImportedClimateObservation(record).to_dict()
        self.assertEqual(imported["station"], "pune central")
        self.assertEqual(imported["city"], "PUNE")


if __name__ == "__main__":
    unittest.main(verbosity=2)

