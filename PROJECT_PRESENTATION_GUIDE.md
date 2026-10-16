# Project Presentation Guide

## Suggested 5-minute demonstration

1. **Overview:** Explain that this is a local Tkinter application with SQLite storage. Point out the record count, average, critical count and station count. Describe the station map as an illustrative visual, not a GIS map.
2. **Records:** Show the imported observations, search for `Pune`, select a row and point out timestamp, temperature, humidity, wind, rainfall and derived alert. Demonstrate a new 38°C row to create a warning if a second example is useful.
3. **Simulation:** Return to Overview and click **START LIVE SIMULATION**. Explain that readings are synthetic and written to SQLite. Stop the feed after a couple of updates.
4. **Critical event:** Click **TRIGGER HEATWAVE EVENT**. The deterministic 41.6°C `Nagpur Heatwave Demo` observation should be marked `CRITICAL`, appear in the latest records/alert feed and remain in the database.
5. **Analysis & alerts:** Show temperature and rainfall summaries, the ≥40°C monitoring count, distinct alert levels, latest station conditions and the warning/advisory text. Explain that the concurrent check uses a bounded worker pool.
6. **Predictions:** Show the last eight stored values and the next-reading trend estimate. Explain its simple calculation and why it is not a trained ML or official forecast.
7. **Project details:** Review the experiment mapping and simulation/source limitations.

## What each screen shows

- **Overview:** SQLite record totals, mean, critical-alert total, distinct stations, illustrative regional station visualization, sensor telemetry, temperature history, recent activity and in-session alert feed.
- **Climate records:** Searchable, scrollable Treeview; editor to add/update/delete; CSV import and report export.
- **Analysis & alerts:** Temperature and rainfall summaries, `NORMAL`/`WARNING`/`CRITICAL` categories, records at or above 40°C and highest-risk observations.
- **Predictions:** A single next-reading estimate derived from up to eight most recent temperature values, with the underlying observations charted.
- **Project details:** Academic concepts and honest limitation notes.

## Academic concepts to point out

- `ClimateObservation` is a class that creates climate reading objects. Its temperature is encapsulated behind a validating property; the type also uses instance, class and static methods.
- `ImportedClimateObservation` inherits from the base climate observation and overrides `to_dict()` to normalize labels.
- `AnalyzerBase` is an abstract class. `HeatwaveAnalyzer` and `RainfallAnalyzer` override `analyze()` and are called through the same interface (polymorphism).
- `HeatwaveAnalyzer` uses a list of temperatures, a tuple of summary values in the interface, a set of alert categories, dictionaries for records/results, lambda expressions, `map()`, `filter()` and `functools.reduce()`.
- `StudentMarks` preserves Experiment 01's four-subject getter/setter exercise. `AcademicMarks → SportsStudentMarks → FinalStudentResult` preserves Experiment 03's three subjects plus sports mark multilevel-inheritance exercise in `experiment_support.py`.
- `weather_data.py` normalizes CSV file input and catches invalid data; `alert_engine.py` classifies heat risk; `database.py` uses SQLite CRUD and aggregate SQL queries.
- `app.py` uses a worker thread, a bounded thread pool, and a queue so simulated readings and analyses do not block main-thread UI updates. The monitoring result includes temperature alert levels plus descriptive humidity and wind watch bands; only temperature controls the three heat alert levels.

See [EXPERIMENT_MAPPING.md](EXPERIMENT_MAPPING.md) for the precise experiment-to-code mapping.

## Data labels and limits

- Imported rows from the supplied files are coursework dataset observations. Do not present every source attribution as independently verified.
- Live feed and the 41.6°C event are synthetic demonstrations.
- The prediction is a heuristic estimate; it is not produced by an ML model and has no confidence range.
- `NORMAL <37°C`, `WARNING ≥37°C and <40°C`, and `CRITICAL ≥40°C` are project demonstration bands, not official IMD heatwave criteria.
- The map is decorative/illustrative and does not display geographic coordinates.
