# Dataset Manifest

All six supplied dataset files are preserved in `data/raw/`. Four are CSV inputs used by the application; two are XLSX companions. Row counts and header schemas below were read from the supplied files. The CSV importer uses Python's `csv` module and field-name normalization in `weather_data.py`.

| File | Rows | Schema / fields | Source information present | Application role and limits |
|---|---:|---|---|---|
| `weather_data exp 03.csv` | 50 | `Station_ID`, `City`, `State`, `Temperature`, `Humidity`, `Condition`, `Wind_Speed` | No source/provenance column. | First-run seed; imports station, city, temperature, humidity, condition and wind. State is not a database field and is not retained. |
| `Exp04_IMD_50_Real_Weather_Observations.csv` | 50 | `Sr_No`, `Date`, `Station`, `Observation_Type`, `Temperature_C`, `Rainfall_mm`, `Source` | `Source` cells name an IMD daily report in Pune dated 2026-09-04. That attribution is reported as written in the file and was not independently verified. | First-run seed; contributes temperature, date, station and rainfall. Humidity and wind are absent and filled with documented importer defaults (50% and 0 km/h); `Sr_No` and observation type are not retained as separate fields. |
| `Pune_Climate_50_Observations EXP 6.csv` | 50 | `Observation_No`, `Date_Time_UTC`, `Station`, `Temperature_C`, `Humidity_Percent` | No source/provenance column. Filename identifies the coursework dataset as Pune climate observations. | First-run seed and Experiment 06 analysis example; parser maps timestamp, station, temperature and humidity. Wind/rainfall are defaulted to zero because they are not supplied. |
| `Weather data (EXP5).csv` | 24,070 | `last_updated_epoch`, `temperature_celsius`, `temperature_fahrenheit`, `wind_mph`, `wind_kph`, `wind_degree`, `wind_direction`, `pressure_mb`, `pressure_in`, `precip_mm`, `precip_in`, `humidity`, `cloud`, `feels_like_celsius`, `feels_like_fahrenheit`, `visibility_km`, `visibility_miles`, `uv_index`, `gust_mph`, `gust_kph` | No source/provenance column. The epoch timestamp and weather fields suggest API-shaped data, but no provider is identified in the file. | Bundled for manual import so the app starts quickly. Parser maps epoch, Celsius temperature, humidity, wind and precipitation. Other columns remain in the source CSV but are not persisted in the SQLite observation schema. Wind is stored in km/h. |
| `Exp04_IMD_50_Real_Weather_Observations.xlsx` | 50 | Same seven column labels as its CSV companion. | Same source cells as the supplied workbook; attribution is not independently verified. | Preserved as a spreadsheet companion. The app's import dialog accepts CSV only. |
| `Weather data (EXP5).xlsx` | 24,070 | Same 20 column labels as its CSV companion. | No provider named in the workbook schema. | Preserved as a spreadsheet companion. Use the `.csv` counterpart to import. |

## Import normalization

- Station, city and condition strings are whitespace-normalized. Imported rows become `ImportedClimateObservation` objects before validation.
- Dates are preserved as text; Unix epoch values are rendered as UTC timestamps.
- Temperature is stored in Celsius. The importer prefers a Celsius column when both Celsius and Fahrenheit are present.
- Humidity defaults to 50%, wind to 0 km/h, and rainfall to 0 mm when a dataset has no corresponding column.
- Rows with missing/non-numeric temperatures or invalid temperature, humidity, wind or rainfall values are skipped. Import shows the count parsed and saved.
- Every record records the generic source label `Imported dataset`; the original source string, if present, is not kept as a separate metadata field in the current SQLite schema. Original CSV/XLSX files remain intact in `data/raw/`.
- Re-importing a dataset inserts duplicates. No deduplication key is defined.

## First-launch seed policy

If the database has zero observations, the app imports the three smaller CSV datasets (`weather_data exp 03.csv`, `Exp04_IMD_50_Real_Weather_Observations.csv`, and `Pune_Climate_50_Observations EXP 6.csv`) for 150 starting records. The 24,070-row dataset is not imported automatically; import it from Climate records when needed.
