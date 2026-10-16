# Climate Intelligence

**Climate Intelligence for Heatwave Monitoring, Prediction and Early Warning** is a local Windows desktop app built with Python, Tkinter and SQLite. It brings together the six programming experiments in a practical climate-monitoring interface.

## Run on Windows

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/) and include Tcl/Tk.
2. Open this folder in VS Code and run `py app.py` in the terminal, or double-click `run_app.bat`.
3. On first launch, the app creates a local SQLite database and loads 150 observations from the three small CSV files. The 24,070-row dataset is available for manual import.

No third-party Python packages are needed; `requirements.txt` is intentionally empty of external dependencies.

## What it includes

- Overview dashboard, searchable climate records, analysis and alerts, trend estimate, and project details.
- SQLite record storage, CSV import/export, validation, synthetic live simulation, and concurrent monitoring.
- Six-experiment mapping, dataset manifest, test suite, presentation guide, and traceability notes.
- Three five-page editable project reports (DOCX) with PDF review copies in [`reports/`](reports/).

## Tests

Run `py -m unittest discover -s tests -v` from this folder. Tests use temporary databases.

## Important limitations

The live simulation and deterministic heatwave demonstration are synthetic. The 37°C/40°C alert bands are classroom settings, not official IMD criteria. The trend feature is a simple estimate, not trained machine learning or an official forecast. The station map is illustrative, not GIS. The supplied datasets' provenance is recorded as provided and not independently verified.

See [DATASET_MANIFEST.md](DATASET_MANIFEST.md), [EXPERIMENT_MAPPING.md](EXPERIMENT_MAPPING.md), and [PROJECT_PRESENTATION_GUIDE.md](PROJECT_PRESENTATION_GUIDE.md) for supporting details.
