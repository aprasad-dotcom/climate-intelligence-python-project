# Climate Intelligence

**Climate Intelligence for Heatwave Monitoring, Prediction and Early Warning** is a local Windows desktop application built with Python, Tkinter and SQLite.

## Run on Windows

1. Install Python 3.10 or newer and include Tcl/Tk.
2. Open this project folder in VS Code.
3. Run `py app.py` in the terminal, or double-click `run_app.bat`.

No third-party Python packages are required.

## Application features

- Dashboard with climate metrics, temperature chart, illustrative station map and alert feed.
- Climate-record table with search, add/edit/delete, CSV import and export.
- Temperature and rainfall analysis, heat-risk categories, concurrent monitoring and a simple trend estimate.
- Synthetic live sensor simulation and a deterministic heatwave demonstration.
- Local SQLite persistence; first launch seeds 150 records from the smaller CSV datasets.

## How the GUI is organized

- `app.py` builds the main Tkinter window, navigation and application screens.
- `ui_components.py` contains reusable panels, metric cards, charts, heat-map canvas and scrollable frame.
- `theme.py` defines the color palette and interface styling.
- `climate_engine.py` validates observations and computes heat/rainfall analysis.
- `alert_engine.py` classifies temperature risk and sensor watch conditions.
- `database.py` manages the SQLite schema, record operations, summaries and CSV export.
- `weather_data.py` parses and normalizes climate CSV datasets.

## Data and tests

The supplied CSV and XLSX files are in `data/raw/`. The app imports CSV files; it keeps the XLSX companions for reference. The 24,070-row Experiment 05 dataset is available for manual import and is not loaded automatically.

Run the tests from this folder with:

```powershell
py -m unittest discover -s tests -v
```

## Limitations

Simulation readings are synthetic. The 37°C warning and 40°C critical thresholds are classroom demonstration settings, not official IMD criteria. The prediction is a simple trend estimate, not trained machine learning or an official forecast. The station map is illustrative rather than GIS.
