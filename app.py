"""Climate Intelligence — heatwave monitoring, prediction and early warning.
Local desktop GUI. Run with: python app.py
"""
import csv
import os
import queue
import random
import sqlite3
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, filedialog, messagebox

from climate_engine import celsius_to_fahrenheit, HeatwaveAnalyzer, RainfallAnalyzer, validate_observation
from alert_engine import classify_alert, monitor_conditions
from database import ClimateDatabase
from theme import *
from ui_components import ScrollableFrame, Panel, ActionButton, MetricCard, TemperatureChart, HeatMapCanvas

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data", "raw")
DB_PATH = os.path.join(APP_DIR, "climate_intelligence.db")


def label(parent, text, size=9, color=TEXT, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=text, bg=bg or parent.cget("bg"), fg=color,
                    font=(FONT, size, "bold" if bold else "normal"), **kwargs)


def panel_title(parent, title, subtitle=None, action=None):
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", padx=15, pady=(13, 8))
    left = tk.Frame(row, bg=PANEL)
    left.pack(side="left", fill="x", expand=True)
    label(left, title, 11, TEXT, True).pack(anchor="w")
    if subtitle:
        label(left, subtitle, 8, MUTED).pack(anchor="w", pady=(3, 0))
    if action:
        action.pack(side="right")
    return row


class ClimateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Climate Intelligence | Heatwave Early Warning")
        # Fit inside typical student laptop displays (including the Windows taskbar).
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        window_w = min(1450, max(880, screen_w - 36))
        window_h = min(820, max(580, screen_h - 90))
        self.geometry(f"{window_w}x{window_h}+12+12")
        self.minsize(min(880, window_w), min(580, window_h))
        self.configure(bg=BG)
        self.db = ClimateDatabase(DB_PATH)
        self.db.seed_from_experiment_csvs(DATA_DIR)
        self.page = "dashboard"
        self.selected_record_id = None
        self.simulation_running = False
        self.stop_event = threading.Event()
        self.events = queue.Queue()
        self.alert_history = []
        self.chart_values = [float(r["temperature"]) for r in reversed(self.db.all(limit=28))]
        self.current_reading = None
        self._configure_ttk()
        self._build_layout()
        self._build_dashboard()
        self._build_records()
        self._build_analysis()
        self._build_predictions()
        self._build_about()
        self.show_page("dashboard")
        self.refresh_all()
        self.after(120, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _configure_ttk(self):
        style = ttk.Style(self)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                        rowheight=29, borderwidth=0, font=(FONT, 9))
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=CYAN,
                        font=(FONT, 9, "bold"), relief="flat", padding=(8, 9))
        style.map("Treeview", background=[("selected", "#27516A")], foreground=[("selected", TEXT)])
        style.configure("Vertical.TScrollbar", background=PANEL_ALT, troughcolor=BG, bordercolor=BG,
                        arrowcolor=MUTED, darkcolor=PANEL_ALT, lightcolor=PANEL_ALT)
        style.configure("TEntry", fieldbackground="#172A3F", foreground=TEXT, padding=7)
        style.configure("TCombobox", fieldbackground="#172A3F", foreground=TEXT, padding=7)
        style.map("TCombobox", fieldbackground=[("readonly", "#172A3F")], foreground=[("readonly", TEXT)])

    def _build_layout(self):
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(shell, bg=SIDEBAR, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=SIDEBAR)
        brand.pack(fill="x", padx=18, pady=(22, 27))
        logo = tk.Canvas(brand, width=42, height=42, bg=SIDEBAR, highlightthickness=0)
        logo.pack(side="left", padx=(0, 10))
        logo.create_oval(3, 3, 39, 39, outline=CYAN, width=2)
        logo.create_arc(8, 8, 34, 34, start=205, extent=230, style="arc", outline=BLUE, width=3)
        logo.create_line(10, 25, 17, 17, 23, 22, 31, 12, fill=CYAN, width=2, smooth=True)
        bt = tk.Frame(brand, bg=SIDEBAR); bt.pack(side="left")
        label(bt, "CLIMATE", 12, TEXT, True).pack(anchor="w")
        label(bt, "INTELLIGENCE", 8, MUTED, True).pack(anchor="w", pady=(1, 0))
        label(self.sidebar, "WORKSPACE", 8, DIM, True).pack(anchor="w", padx=20, pady=(0, 9))
        self.nav = {}
        for title, key, icon in [("Overview", "dashboard", "◈"), ("Climate records", "records", "▤"),
                                 ("Analysis & alerts", "analysis", "⌁"), ("Predictions", "predictions", "↗"),
                                 ("Project details", "about", "ⓘ")]:
            btn = tk.Button(self.sidebar, text=f"  {icon}   {title}", command=lambda k=key: self.show_page(k),
                            bg=SIDEBAR, fg=MUTED, activebackground="#18364F", activeforeground=TEXT,
                            relief="flat", bd=0, highlightthickness=0, highlightbackground=SIDEBAR,
                            highlightcolor=SIDEBAR, takefocus=0, anchor="w", padx=15, pady=13, cursor="hand2",
                            font=(FONT, 10, "bold"))
            btn.pack(fill="x", padx=8, pady=2)
            self.nav[key] = btn
        tk.Frame(self.sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        side_status = tk.Frame(self.sidebar, bg="#0E2032", highlightbackground=BORDER, highlightthickness=1)
        side_status.pack(fill="x", padx=12, pady=12)
        label(side_status, "SENSOR NETWORK", 8, MUTED, True).pack(anchor="w", padx=12, pady=(11, 4))
        self.side_live = label(side_status, "●  STANDBY", 9, AMBER, True)
        self.side_live.pack(anchor="w", padx=12)
        label(side_status, "LOCAL SQLITE STORAGE", 7, DIM, True).pack(anchor="w", padx=12, pady=(5, 11))
        label(self.sidebar, "KJSCE  •  PYTHON MINI PROJECT", 7, DIM, True).pack(anchor="w", padx=14, pady=(0, 15))

        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.topbar = tk.Frame(main, bg=TOPBAR, height=55, highlightbackground=BORDER, highlightthickness=0)
        self.topbar.pack(fill="x"); self.topbar.pack_propagate(False)
        label(self.topbar, "HEAT RISK OPERATIONS  /  MAHARASHTRA", 9, MUTED, True, bg=TOPBAR).pack(side="left", padx=22)
        right = tk.Frame(self.topbar, bg=TOPBAR); right.pack(side="right", padx=16)
        self.clock = label(right, "", 8, MUTED, bg=TOPBAR); self.clock.pack(side="left", padx=(0, 12))
        ActionButton(right, "＋  ADD OBSERVATION", lambda: self.show_page("records"), "primary", compact=True).pack(side="left")
        self._tick_clock()
        self.workspace = ScrollableFrame(main, bg=BG)
        self.workspace.pack(fill="both", expand=True, padx=(18, 12), pady=(15, 10))
        self.pages = {}
        statusbar = tk.Frame(main, bg=TOPBAR, height=26); statusbar.pack(fill="x", side="bottom"); statusbar.pack_propagate(False)
        self.status_var = tk.StringVar(value="Ready • Experiment datasets loaded into local SQLite")
        label(statusbar, "●", 8, GREEN, bg=TOPBAR).pack(side="left", padx=(12, 5))
        tk.Label(statusbar, textvariable=self.status_var, bg=TOPBAR, fg=MUTED, anchor="w", font=(FONT, 8)).pack(side="left", fill="x", expand=True)

    def _tick_clock(self):
        if hasattr(self, "clock"):
            self.clock.configure(text=datetime.now().strftime("%a, %d %b %Y   •   %H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _new_page(self, key):
        frame = tk.Frame(self.workspace.inner, bg=BG)
        self.pages[key] = frame
        return frame

    def _heading(self, parent, title, subtitle, tag="CLIMATE INTELLIGENCE"):
        row = tk.Frame(parent, bg=BG); row.pack(fill="x", pady=(1, 15))
        left = tk.Frame(row, bg=BG); left.pack(side="left", fill="x", expand=True)
        label(left, tag, 8, CYAN, True, bg=BG).pack(anchor="w", pady=(0, 5))
        label(left, title, 21, TEXT, True, bg=BG).pack(anchor="w")
        label(left, subtitle, 9, MUTED, bg=BG).pack(anchor="w", pady=(4, 0))
        return row

    def show_page(self, key):
        self.page = key
        for frame in self.pages.values(): frame.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.workspace.scroll_to_top()
        for k, btn in self.nav.items():
            btn.configure(bg="#17364F" if k == key else SIDEBAR, fg=CYAN if k == key else MUTED)
        if key == "dashboard": self.refresh_dashboard()
        elif key == "records": self.refresh_records()
        elif key == "analysis": self.refresh_analysis()
        elif key == "predictions": self.refresh_predictions()

    def _build_dashboard(self):
        p = self._new_page("dashboard")
        hero = self._heading(p, "Heatwave monitoring overview",
            "A live command view for climate observations, heat-risk signals and early-warning review.", "CLIMATE INTELLIGENCE  /  OPERATIONS")
        actions = tk.Frame(hero, bg=BG); actions.pack(side="right", anchor="e", pady=(17, 0))
        self.dashboard_start = ActionButton(actions, "▶  START LIVE SIMULATION", self.start_simulation, "primary", compact=True)
        self.dashboard_start.pack(side="left", padx=(0, 7))
        self.dashboard_stop = ActionButton(actions, "■  STOP", self.stop_simulation, "danger", compact=True)
        self.dashboard_stop.pack(side="left")

        metrics = tk.Frame(p, bg=BG); metrics.pack(fill="x", pady=(0, 13))
        for i in range(4): metrics.grid_columnconfigure(i, weight=1, uniform="metric")
        self.metrics = {}
        metric_specs = [("total", "Observations", "0", "Stored climate records", BLUE, "▤"),
                        ("avg", "Mean temperature", "—°C", "Across all readings", CYAN, "◉"),
                        ("critical", "Critical alerts", "0", "At or above 40°C", RED, "⚠"),
                        ("stations", "Stations monitored", "0", "Distinct station labels", PURPLE, "⌖")]
        for i, spec in enumerate(metric_specs):
            key, title, value, subtitle, accent, icon = spec
            card = MetricCard(metrics, title, value, subtitle, accent, icon)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 9, 0))
            self.metrics[key] = card

        row1 = tk.Frame(p, bg=BG); row1.pack(fill="x", pady=(0, 13))
        row1.grid_columnconfigure(0, weight=7, uniform="upper")
        row1.grid_columnconfigure(1, weight=4, uniform="upper")
        map_panel = Panel(row1); map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_title(map_panel, "Regional heat-risk map", "Station network • alert colour coding • illustrative map")
        self.map_canvas = HeatMapCanvas(map_panel, height=290)
        self.map_canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        map_legend = tk.Frame(map_panel, bg=PANEL); map_legend.pack(fill="x", padx=14, pady=(0, 11))
        for color, txt in [(GREEN,"NORMAL"),(AMBER,"WARNING"),(RED,"CRITICAL")]:
            tk.Label(map_legend, text=f"●  {txt}", bg=PANEL, fg=color, font=(FONT, 8, "bold")).pack(side="left", padx=(0, 16))
        self.sensor_panel = Panel(row1, bg="#10283D"); self.sensor_panel.grid(row=0, column=1, sticky="nsew")
        label(self.sensor_panel, "LIVE SENSOR TELEMETRY", 8, CYAN, True, bg="#10283D").pack(anchor="w", padx=16, pady=(15, 4))
        self.sensor_temp = label(self.sensor_panel, "—.-°C", 32, TEXT, True, bg="#10283D"); self.sensor_temp.pack(anchor="w", padx=15, pady=(3, 0))
        self.sensor_caption = label(self.sensor_panel, "Waiting for simulated readings", 8, MUTED, bg="#10283D"); self.sensor_caption.pack(anchor="w", padx=16, pady=(0, 12))
        self.sensor_badge = tk.Label(self.sensor_panel, text="●  STANDBY", bg="#28394B", fg=AMBER,
                                     font=(FONT, 10, "bold"), padx=10, pady=9)
        self.sensor_badge.pack(fill="x", padx=14, pady=(0, 11))
        self.sensor_humidity = label(self.sensor_panel, "HUMIDITY     — %", 9, TEXT, bg="#10283D"); self.sensor_humidity.pack(anchor="w", padx=16, pady=5)
        self.sensor_wind = label(self.sensor_panel, "WIND              — km/h", 9, TEXT, bg="#10283D"); self.sensor_wind.pack(anchor="w", padx=16, pady=5)
        self.sensor_station = label(self.sensor_panel, "STATION        Pune Central", 9, TEXT, bg="#10283D"); self.sensor_station.pack(anchor="w", padx=16, pady=5)
        tk.Frame(self.sensor_panel, bg=BORDER, height=1).pack(fill="x", padx=14, pady=11)
        self.sensor_reading_note = label(self.sensor_panel, "Synthetic local sensor feed", 8, MUTED, bg="#10283D"); self.sensor_reading_note.pack(anchor="w", padx=16, pady=(0, 8))
        ActionButton(self.sensor_panel, "⚠  TRIGGER HEATWAVE EVENT", self.trigger_heatwave_event,
                     "danger", compact=True).pack(fill="x", padx=14, pady=(0, 12))

        row2 = tk.Frame(p, bg=BG); row2.pack(fill="x", pady=(0, 13))
        row2.grid_columnconfigure(0, weight=7, uniform="lower")
        row2.grid_columnconfigure(1, weight=4, uniform="lower")
        chart_panel = Panel(row2); chart_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_title(chart_panel, "Temperature stream", "Live readings over time • educational alert thresholds")
        self.chart = TemperatureChart(chart_panel, height=230)
        self.chart.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        self.trend_panel = Panel(row2)
        self.trend_panel.grid(row=0, column=1, sticky="nsew")
        panel_title(self.trend_panel, "Near-term trend estimate", "A simple trend heuristic, not a trained ML model")
        self.forecast_temp = label(self.trend_panel, "—.-°C", 28, CYAN, True); self.forecast_temp.pack(anchor="w", padx=16, pady=(4, 0))
        self.forecast_direction = label(self.trend_panel, "Awaiting more readings", 9, MUTED); self.forecast_direction.pack(anchor="w", padx=16, pady=(0, 14))
        tk.Frame(self.trend_panel, bg=BORDER, height=1).pack(fill="x", padx=15, pady=(0, 11))
        self._mini_stat(self.trend_panel, "Warning threshold", "37.0°C", AMBER)
        self._mini_stat(self.trend_panel, "Critical threshold", "40.0°C", RED)
        self._mini_stat(self.trend_panel, "Data source", "CSV + simulation", BLUE)
        label(self.trend_panel, "Thresholds are for the academic demo only.", 7, DIM).pack(anchor="w", padx=15, pady=(10, 13))

        row3 = tk.Frame(p, bg=BG); row3.pack(fill="x", pady=(0, 14))
        row3.grid_columnconfigure(0, weight=7, uniform="last")
        row3.grid_columnconfigure(1, weight=4, uniform="last")
        activity = Panel(row3); activity.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        panel_title(activity, "Recent station activity", "Latest stored readings • select a row in Climate records to edit it")
        self.latest_tree = self._make_tree(activity,
            [("station","Station",140),("city","City",115),("temperature","Temp °C",82),
             ("humidity","Humidity",82),("alert","Alert level",100)], height=6)
        self.latest_tree.wrapper.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.latest_tree.tag_configure("CRITICAL", foreground=RED)
        self.latest_tree.tag_configure("WARNING", foreground=AMBER)
        alerts = Panel(row3); alerts.grid(row=0, column=1, sticky="nsew")
        panel_title(alerts, "Event & alert feed", "New warnings generated during this session")
        self.alert_text = tk.Text(alerts, height=8, bg=PANEL, fg=TEXT, relief="flat", bd=0,
                                  font=(FONT, 8), padx=13, pady=7, wrap="word", insertbackground=TEXT)
        self.alert_text.pack(fill="both", expand=True, padx=7, pady=(0, 8))
        self.alert_text.tag_configure("CRITICAL", foreground=RED)
        self.alert_text.tag_configure("WARNING", foreground=AMBER)
        self.alert_text.tag_configure("NORMAL", foreground=GREEN)

    def _mini_stat(self, parent, title, value, color):
        row = tk.Frame(parent, bg=PANEL); row.pack(fill="x", padx=15, pady=4)
        label(row, title, 8, MUTED).pack(side="left")
        label(row, value, 8, color, True).pack(side="right")

    def _make_tree(self, parent, columns, height=8):
        container = tk.Frame(parent, bg=PANEL)
        tree = ttk.Treeview(container, columns=[c[0] for c in columns], show="headings", height=height, selectmode="browse")
        for key, title, width in columns:
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=55, anchor="center", stretch=True)
        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        tree.tag_configure("CRITICAL", foreground=RED)
        tree.tag_configure("WARNING", foreground=AMBER)
        tree.tag_configure("NORMAL", foreground=TEXT)
        tree.wrapper = container
        return tree

    def _build_records(self):
        p = self._new_page("records")
        self._heading(p, "Climate records", "Search and manage the climate dataset. Select a row to load it into the editor.", "DATA MANAGEMENT  /  SQLITE")
        toolbar = Panel(p); toolbar.pack(fill="x", pady=(0, 12))
        bar = tk.Frame(toolbar, bg=PANEL); bar.pack(fill="x", padx=12, pady=11)
        label(bar, "OBSERVATION REGISTER", 9, TEXT, True).pack(side="left", padx=(0, 14))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(bar, textvariable=self.search_var, width=25)
        search_entry.pack(side="left", padx=(0, 7)); search_entry.bind("<Return>", lambda _e: self.refresh_records())
        ActionButton(bar, "⌕  SEARCH", self.refresh_records, "secondary", compact=True).pack(side="left", padx=(0, 7))
        ActionButton(bar, "⇧  IMPORT CSV", self.import_csv, "green", compact=True).pack(side="left", padx=(0, 7))
        ActionButton(bar, "⇩  EXPORT CSV", self.export_report, "blue", compact=True).pack(side="left")
        self.records_count = label(bar, "0 records", 8, MUTED, bg=PANEL); self.records_count.pack(side="right")

        table_panel = Panel(p); table_panel.pack(fill="both", expand=True, pady=(0, 12))
        panel_title(table_panel, "Observation table", "Click any row to select it • use the editor below to update it")
        self.records_tree = self._make_tree(table_panel,
            [("id","ID",48),("date","Date / time",150),("station","Station",140),("city","City",125),
             ("temperature","Temp °C",80),("humidity","Humidity %",85),("wind","Wind km/h",85),
             ("rain","Rain mm",75),("alert","Alert",95)], height=10)
        self.records_tree.wrapper.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.records_tree.bind("<<TreeviewSelect>>", self._on_record_select)
        self.records_tree.bind("<Double-1>", self._on_record_select)

        editor = Panel(p); editor.pack(fill="x", pady=(0, 14))
        panel_title(editor, "Observation editor", "Add a new record or select an existing record above to edit it")
        form = tk.Frame(editor, bg=PANEL); form.pack(fill="x", padx=14, pady=(0, 12))
        field_specs = [
            ("observed_at","Date / time",datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("station","Station","Pune Central"),("city","City","Pune"),
            ("temperature","Temperature °C","38.0"),("humidity","Humidity %","55"),
            ("wind_speed","Wind km/h","10"),("rainfall","Rainfall mm","0"),
            ("condition_text","Condition","Hot"),("source","Source","Manual entry")]
        self.form_vars = {}
        for i,(key,title,default) in enumerate(field_specs):
            col=i%3; row=i//3
            cell=tk.Frame(form,bg=PANEL); cell.grid(row=row,column=col,sticky="ew",padx=(0 if col==0 else 12,8),pady=5)
            label(cell,title.upper(),7,MUTED,True).pack(anchor="w",pady=(0,4))
            var=tk.StringVar(value=default); self.form_vars[key]=var
            ttk.Entry(cell,textvariable=var).pack(fill="x")
        for i in range(3): form.grid_columnconfigure(i,weight=1,uniform="fields")
        label(form,"NOTES",7,MUTED,True).grid(row=3,column=0,sticky="w",pady=(7,4))
        self.form_vars["notes"] = tk.StringVar(value="")
        ttk.Entry(form,textvariable=self.form_vars["notes"]).grid(row=4,column=0,columnspan=3,sticky="ew",pady=(0,9))
        buttons=tk.Frame(form,bg=PANEL); buttons.grid(row=5,column=0,columnspan=3,sticky="w",pady=(3,0))
        ActionButton(buttons,"＋  SAVE NEW",self.save_record,"primary",compact=True).pack(side="left",padx=(0,7))
        ActionButton(buttons,"✓  UPDATE SELECTED",self.update_record,"blue",compact=True).pack(side="left",padx=(0,7))
        ActionButton(buttons,"⌫  DELETE SELECTED",self.delete_record,"danger",compact=True).pack(side="left",padx=(0,7))
        ActionButton(buttons,"CLEAR FORM",self.clear_form,"secondary",compact=True).pack(side="left")

        library=Panel(p); library.pack(fill="x",pady=(0,14))
        panel_title(library,"Bundled experiment datasets","Use Import CSV to load a file. The three small climate-use-case datasets are loaded on first launch.")
        list_frame=tk.Frame(library,bg=PANEL); list_frame.pack(fill="x",padx=14,pady=(0,12))
        self.dataset_status=[]
        for fname,desc in [("weather_data exp 03.csv","Experiment 03 • string handling / inheritance dataset"),
                           ("Exp04_IMD_50_Real_Weather_Observations.csv","Experiment 04 • 50 IMD observations"),
                           ("Weather data (EXP5).csv","Experiment 05 • larger weather dataset (24k rows)"),
                           ("Pune_Climate_50_Observations EXP 6.csv","Experiment 06 • collections / functional programming")]:
            line=tk.Frame(list_frame,bg=PANEL_ALT); line.pack(fill="x",pady=3)
            label(line,f"▤  {fname}",8,TEXT,True,bg=PANEL_ALT).pack(side="left",padx=10,pady=8)
            label(line,desc,8,MUTED,bg=PANEL_ALT).pack(side="left",padx=10)
            ActionButton(line,"IMPORT",lambda n=fname:self.import_named_dataset(n),"quiet",compact=True).pack(side="right",padx=7,pady=4)

    def _build_analysis(self):
        p=self._new_page("analysis")
        self._heading(p,"Analysis & early warnings","Summary statistics, heat-risk classification and a concurrent monitoring check.","CLIMATE ANALYTICS  /  ALERT REVIEW")
        actions=tk.Frame(p,bg=BG); actions.pack(fill="x",pady=(0,12))
        ActionButton(actions,"⌁  RUN CONCURRENT MONITORING",self.run_monitor,"primary",compact=True).pack(side="left")
        ActionButton(actions,"⇩  EXPORT REPORT",self.export_report,"blue",compact=True).pack(side="left",padx=8)
        ActionButton(actions,"↻  REFRESH ANALYSIS",self.refresh_analysis,"secondary",compact=True).pack(side="left")
        self.analysis_metrics=tk.Frame(p,bg=BG); self.analysis_metrics.pack(fill="x",pady=(0,12))
        for i in range(3): self.analysis_metrics.grid_columnconfigure(i,weight=1,uniform="a")
        self.analysis_cards=[]
        for i,(title,value,subtitle,color) in enumerate([("MEAN TEMPERATURE","—","Across observations",CYAN),
            ("HEAT MONITOR READINGS","—","At or above 40°C",AMBER),("ALERT CATEGORIES","—","Distinct classifications",PURPLE)]):
            c=MetricCard(self.analysis_metrics,title,value,subtitle,color,"◉")
            c.grid(row=0,column=i,sticky="ew",padx=(0 if i==0 else 9,0));self.analysis_cards.append(c)
        summary=Panel(p); summary.pack(fill="x",pady=(0,12))
        panel_title(summary,"Processing summary","Includes Python collection and functional-programming operations")
        self.analysis_summary=tk.Text(summary,height=10,bg=PANEL,fg=TEXT,relief="flat",bd=0,font=(MONO,9),padx=15,pady=10,wrap="word",insertbackground=TEXT)
        self.analysis_summary.pack(fill="x",padx=8,pady=(0,8))
        alerts=Panel(p); alerts.pack(fill="both",expand=True,pady=(0,14))
        panel_title(alerts,"Highest-risk observations","The hottest stored records, ranked by temperature")
        self.analysis_tree=self._make_tree(alerts,[("station","Station",150),("city","City",140),("temp","Temp °C",90),
            ("humidity","Humidity %",100),("wind","Wind km/h",100),("alert","Alert level",120)],height=9)
        self.analysis_tree.wrapper.pack(fill="both",expand=True,padx=10,pady=(0,10))

    def _build_predictions(self):
        p = self._new_page("predictions")
        self._heading(p, "Temperature trend estimate",
                      "A transparent next-reading estimate based on the most recent stored observations.",
                      "PREDICTIONS  /  SIMPLE LINEAR TREND")
        panel = Panel(p); panel.pack(fill="x", pady=(0, 12))
        panel_title(panel, "Estimated next reading", "A lightweight trend heuristic, not a trained model or official forecast.")
        self.prediction_temp = label(panel, "—.-°C", 32, CYAN, True)
        self.prediction_temp.pack(anchor="w", padx=18, pady=(0, 3))
        self.prediction_direction = label(panel, "Waiting for observations", 10, MUTED)
        self.prediction_direction.pack(anchor="w", padx=18, pady=(0, 8))
        self.prediction_basis = label(panel, "Based on 0 recent readings", 8, DIM)
        self.prediction_basis.pack(anchor="w", padx=18, pady=(0, 14))
        chart_panel = Panel(p); chart_panel.pack(fill="both", expand=True, pady=(0, 12))
        panel_title(chart_panel, "Recent temperature observations", "Stored values in chronological order; synthetic rows are labelled in the records table.")
        self.prediction_chart = TemperatureChart(chart_panel, height=300)
        self.prediction_chart.pack(fill="both", expand=True, padx=8, pady=(0, 10))
        note = Panel(p); note.pack(fill="x", pady=(0, 14))
        panel_title(note, "How to read this estimate")
        label(note, "The app takes up to the latest eight readings, calculates the average per-reading change from the first to last, then adds that change once to the latest value. The output is only an educational estimate for the next observation interval. It has no calibrated confidence range and must not be used for safety decisions.", 9, MUTED, wraplength=980, justify="left").pack(anchor="w", padx=15, pady=(0, 14))

    def _build_about(self):
        p=self._new_page("about")
        self._heading(p,"Project details","The assignment is implemented as a local Python desktop GUI, not a deployed website.","PROJECT NOTES  /  LAB ALIGNMENT")
        cards=[
            ("01  •  OBJECT-ORIENTED PYTHON","Classes and objects, attributes and methods, constructors, and list-based observation handling.",BLUE),
            ("02  •  STRING HANDLING & INHERITANCE","Normalize imported station names and condition labels; use inherited climate analysis behaviour.",CYAN),
            ("03  •  ABSTRACT CLASSES & POLYMORPHISM","An abstract analyzer interface and concrete HeatwaveAnalyzer implementation share one analysis contract.",PURPLE),
            ("04  •  EXCEPTIONS, MODULES & THREADING","Separate modules, validated input, handled errors, and background simulated readings with main-thread UI updates.",AMBER),
            ("05  •  COLLECTIONS & FUNCTIONAL PROGRAMMING","Lists, tuples, sets, dictionaries, lambda, map(), filter() and reduce() analyse the climate records.",GREEN),
            ("06  •  SQLITE & DATASET WORKFLOW","Persistent records with create/read/update/delete/search, aggregate queries, CSV import and report export.",BLUE),
        ]
        for title,desc,color in cards:
            c=Panel(p);c.pack(fill="x",pady=(0,9))
            tk.Frame(c,bg=color,width=4).pack(side="left",fill="y")
            label(c,title,10,color,True).pack(anchor="w",padx=16,pady=(12,4))
            label(c,desc,9,MUTED,wraplength=1000,justify="left").pack(anchor="w",padx=16,pady=(0,13))
        note=Panel(p);note.pack(fill="x",pady=(0,14))
        panel_title(note,"Simulation and academic-use note")
        label(note,"The live feed generates synthetic local readings to demonstrate monitoring, alert generation, concurrency and database updates. It does not connect to physical sensors or a live weather API. The near-term temperature estimate is a simple trend heuristic, not a trained machine-learning model. Demo thresholds (NORMAL below 37°C, WARNING from 37°C to below 40°C, CRITICAL at or above 40°C) are not official IMD heatwave criteria.",9,MUTED,wraplength=1000,justify="left").pack(anchor="w",padx=15,pady=(0,15))

    # ----------------------------- Database UI -----------------------------
    def _form_record(self):
        def number(key):
            try: return float(self.form_vars[key].get().strip())
            except ValueError as exc: raise ValueError(f"Enter a valid number for {key.replace('_',' ')}.") from exc
        r={key:var.get().strip() for key,var in self.form_vars.items()}
        r["temperature"]=number("temperature");r["humidity"]=number("humidity")
        r["wind_speed"]=number("wind_speed");r["rainfall"]=number("rainfall")
        validate_observation(r)
        return r

    def save_record(self):
        try:
            self.db.add(self._form_record());self.current_reading=None;self.clear_form();self.refresh_all()
            self.status_var.set("New observation saved to SQLite.")
        except (ValueError,sqlite3.Error) as exc: messagebox.showerror("Cannot save observation",str(exc))

    def update_record(self):
        if self.selected_record_id is None:
            messagebox.showinfo("Select a record","Click a row in the observation table first.");return
        try:
            self.db.update(self.selected_record_id,self._form_record());self.current_reading=None;self.refresh_all()
            self.status_var.set(f"Observation #{self.selected_record_id} updated.")
        except (ValueError,sqlite3.Error) as exc: messagebox.showerror("Cannot update observation",str(exc))

    def delete_record(self):
        if self.selected_record_id is None:
            messagebox.showinfo("Select a record","Click a row in the observation table first.");return
        if messagebox.askyesno("Confirm delete",f"Delete observation #{self.selected_record_id}? This cannot be undone."):
            rid=self.selected_record_id;self.db.delete(rid);self.current_reading=None;self.clear_form();self.refresh_all()
            self.status_var.set(f"Observation #{rid} deleted.")

    def clear_form(self):
        self.selected_record_id=None
        defaults={"observed_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"station":"Pune Central","city":"Pune",
            "temperature":"38.0","humidity":"55","wind_speed":"10","rainfall":"0","condition_text":"Hot","source":"Manual entry","notes":""}
        for key,value in defaults.items(): self.form_vars[key].set(value)
        if hasattr(self,"records_tree"):
            self.records_tree.selection_remove(self.records_tree.selection())

    def _on_record_select(self,_event=None):
        selection=self.records_tree.selection()
        if not selection:return
        values=self.records_tree.item(selection[0],"values")
        if not values:return
        record=self.db.get(int(values[0]))
        if not record:return
        self.selected_record_id=record["id"]
        for key,var in self.form_vars.items():var.set(str(record.get(key,"") if record.get(key) is not None else ""))
        self.status_var.set(f"Selected observation #{self.selected_record_id}; edit values below and click UPDATE SELECTED.")

    def refresh_records(self):
        if not hasattr(self,"records_tree"):return
        for item in self.records_tree.get_children():self.records_tree.delete(item)
        query = self.search_var.get() if hasattr(self,"search_var") else ""
        total_matches = self.db.count(query)
        rows=self.db.all(query, limit=1000)
        suffix = f"Showing {len(rows):,} of {total_matches:,} matching records" if total_matches > len(rows) else f"{total_matches:,} matching records"
        self.records_count.configure(text=suffix)
        for r in rows:
            vals=(r["id"],r["observed_at"],r["station"],r["city"],f'{r["temperature"]:.1f}',f'{r["humidity"]:.0f}',
                  f'{r["wind_speed"]:.1f}',f'{r["rainfall"]:.1f}',r["alert_level"])
            self.records_tree.insert("","end",values=vals,tags=(r["alert_level"],))

    def refresh_dashboard(self):
        if not hasattr(self,"metrics"):return
        summary=self.db.summary()
        self.metrics["total"].set_value(f'{summary["total"]:,}')
        self.metrics["avg"].set_value(f'{summary["avg_temp"]:.1f}°C')
        self.metrics["critical"].set_value(str(summary["critical"] or 0),f'{summary["warning"] or 0} warning-level records')
        self.metrics["stations"].set_value(str(summary["stations"] or 0))
        latest=self.db.all(limit=10)
        history=list(reversed(self.db.all(limit=36)))
        self.chart_values=[float(r["temperature"]) for r in history]
        for item in self.latest_tree.get_children():self.latest_tree.delete(item)
        for r in latest:
            self.latest_tree.insert("","end",values=(r["station"],r["city"],f'{r["temperature"]:.1f}',f'{r["humidity"]:.0f}',r["alert_level"]),tags=(r["alert_level"],))
        self.chart.set_values(self.chart_values)
        self.map_canvas.set_stations(latest)
        if self.current_reading is None and latest:
            last = latest[0]
            self.sensor_temp.configure(text=f'{last["temperature"]:.1f}°C')
            self.sensor_humidity.configure(text=f'HUMIDITY     {last["humidity"]:.0f}%')
            self.sensor_wind.configure(text=f'WIND              {last["wind_speed"]:.1f} km/h')
            self.sensor_station.configure(text=f'STATION        {last["station"]}')
            self.sensor_caption.configure(text="Latest stored observation • simulation paused")
            level = last["alert_level"]
            self.sensor_badge.configure(text=f'●  STANDBY  /  LAST: {level}', fg=ALERT_COLORS[level], bg="#28394B")
        self._update_forecast()
        self._render_alert_feed()

    def _update_forecast(self):
        if not hasattr(self,"forecast_temp"):return
        vals=self.chart_values[-8:]
        if not vals:
            self.forecast_temp.configure(text="—.-°C");self.forecast_direction.configure(text="Awaiting more readings");return
        estimate=vals[-1]
        if len(vals)>=2:
            delta=(vals[-1]-vals[0])/max(1,len(vals)-1)
            estimate=vals[-1]+delta
            direction="Rising" if delta>0.15 else "Falling" if delta < -0.15 else "Relatively stable"
            direction += f" • trend {delta:+.2f}° per reading"
        else: direction="Collecting more readings"
        self.forecast_temp.configure(text=f"{estimate:.1f}°C",fg=RED if estimate>=40 else AMBER if estimate>=37 else CYAN)
        self.forecast_direction.configure(text=direction)
        if hasattr(self, "prediction_temp"):
            self.prediction_temp.configure(text=f"{estimate:.1f}°C", fg=RED if estimate >= 40 else AMBER if estimate >= 37 else CYAN)
            self.prediction_direction.configure(text=direction)

    def _render_alert_feed(self):
        if not hasattr(self,"alert_text"):return
        self.alert_text.configure(state="normal");self.alert_text.delete("1.0","end")
        if not self.alert_history:
            self.alert_text.insert("end","No new simulated alerts in this session.\n\nStart the live simulation to watch new station readings and heat-risk events.")
        else:
            for event in reversed(self.alert_history[-9:]):
                self.alert_text.insert("end",f'{event["time"]}   {event["station"]}\n',event["level"])
                self.alert_text.insert("end",f'{event["temperature"]:.1f}°C  •  {event["level"]}\n\n',event["level"])
        self.alert_text.configure(state="disabled")

    def refresh_analysis(self):
        if not hasattr(self,"analysis_summary"):return
        rows=self.db.all()
        result=HeatwaveAnalyzer().analyze(rows)
        rainfall_result=RainfallAnalyzer().analyze(rows)
        levels={r["alert_level"] for r in rows}  # set collection
        # tuple used to keep a compact immutable summary for this analysis run
        summary_tuple=(result["count"],result["average"],result["maximum"],result["minimum"])
        self.analysis_cards[0].set_value(f'{result["average"]:.2f}°C')
        self.analysis_cards[1].set_value(str(result["hot_count"]))
        self.analysis_cards[2].set_value(str(len(levels)))
        lines=["CLIMATE DATA PROCESSING SUMMARY",""]
        lines.append(f"Records processed             : {summary_tuple[0]:,}")
        lines.append(f"Average temperature           : {summary_tuple[1]:.2f}°C / {celsius_to_fahrenheit(summary_tuple[1]):.2f}°F")
        lines.append(f"Minimum / maximum             : {summary_tuple[3]:.1f}°C / {summary_tuple[2]:.1f}°C" if summary_tuple[0] else "Minimum / maximum             : —")
        lines.append(f"Readings at or above 40°C     : {result['hot_count']}")
        lines.append(f"Total temperature             : {result['total']:.2f}°C")
        lines.append(f"Rainfall total / wet readings : {rainfall_result['total_rainfall']:.1f} mm / {rainfall_result['wet_readings']}")
        lines.append(f"Square of first temperature   : {result['square_first']:.2f}" if result["square_first"] is not None else "Square of first temperature   : —")
        if rows:
            latest = max(rows, key=lambda item: item["id"])
            lines.append(f"Latest station / city         : {latest['station']} / {latest['city']}")
            lines.append(f"Latest conditions             : {latest['temperature']:.1f}°C, {latest['humidity']:.0f}% RH, {latest['wind_speed']:.1f} km/h wind")
            lines.append(f"Weather description           : {latest['condition_text'] or 'Not specified'}")
            lines.append(f"Current alert                 : {latest['alert_level']}")
            lines.append("AI advisory                   : High temperatures require continued observation and an early warning review." if latest["alert_level"] != "NORMAL" else "AI advisory                   : Conditions are below the configured demo warning threshold.")
        lines.append(f"Alert levels present          : {', '.join(sorted(levels)) if levels else 'None'}")
        lines.append("\nMETHODS DEMONSTRATED")
        lines.append("• list: temperature collection")
        lines.append("• tuple: compact analysis summary")
        lines.append("• set: unique alert categories")
        lines.append("• dictionary: structured observation and result records")
        lines.append("• lambda + map(): normalize temperature values and convert °C → °F")
        lines.append("• filter(): identify readings at or above 40°C for heatwave monitoring")
        lines.append("• reduce(): aggregate the temperature total for the mean")
        lines.append("\nThe next-value estimate on Overview is a simple trend heuristic, not a trained ML forecast.")
        self.analysis_summary.configure(state="normal");self.analysis_summary.delete("1.0","end")
        self.analysis_summary.insert("end","\n".join(lines));self.analysis_summary.configure(state="disabled")
        for item in self.analysis_tree.get_children():self.analysis_tree.delete(item)
        for r in sorted(rows,key=lambda item:item["temperature"],reverse=True)[:50]:
            self.analysis_tree.insert("","end",values=(r["station"],r["city"],f'{r["temperature"]:.1f}',f'{r["humidity"]:.0f}',f'{r["wind_speed"]:.1f}',r["alert_level"]),tags=(r["alert_level"],))

    def refresh_predictions(self):
        if not hasattr(self, "prediction_chart"):
            return
        rows = list(reversed(self.db.all(limit=8)))
        self.prediction_chart.set_values([float(row["temperature"]) for row in rows])
        self._update_forecast()
        self.prediction_basis.configure(text=f"Based on {len(rows)} latest stored readings • observations are not time-normalized")

    def refresh_all(self):
        self.refresh_dashboard();self.refresh_records();self.refresh_analysis()

    # ----------------------------- Dataset actions -----------------------------
    def import_csv(self):
        path=filedialog.askopenfilename(title="Import a climate experiment CSV",initialdir=DATA_DIR,
            filetypes=[("CSV datasets","*.csv"),("All files","*.*")])
        if path:self._import_path(path)

    def import_named_dataset(self,filename):
        path=os.path.join(DATA_DIR,filename)
        if not os.path.isfile(path):
            messagebox.showerror("Dataset not found",f"Could not find {filename} in the project's data folder.");return
        self._import_path(path)

    def _import_path(self,path):
        try:
            parsed=self.db.import_csv(path);self.current_reading=None
            self.refresh_all();self.status_var.set(f"Imported {parsed[0]:,} records from {os.path.basename(path)}.")
            messagebox.showinfo("Import complete",f"Valid rows parsed: {parsed[1]:,}\nRows saved: {parsed[0]:,}\n\nSource: {os.path.basename(path)}")
        except (OSError,ValueError,csv.Error) as exc:messagebox.showerror("Import failed",str(exc))

    def export_report(self):
        path=filedialog.asksaveasfilename(title="Export climate report",defaultextension=".csv",
            initialfile="climate_intelligence_report.csv",filetypes=[("CSV report","*.csv")])
        if not path:return
        try:
            count=self.db.export_csv(path)
            messagebox.showinfo("Export complete",f"Exported {count:,} records to:\n{path}")
        except OSError as exc:messagebox.showerror("Export failed",str(exc))

    # ----------------------------- Simulation & threading -----------------------------
    def start_simulation(self):
        if self.simulation_running:return
        self.simulation_running=True
        self.stop_event = threading.Event()
        active_stop_event = self.stop_event
        self.dashboard_start.configure(state="disabled",text="●  SIMULATION RUNNING")
        self.side_live.configure(text="●  LIVE SIMULATION",fg=GREEN)
        self.sensor_caption.configure(text="Receiving simulated readings",fg=GREEN)
        self.sensor_badge.configure(text="●  LIVE FEED",bg="#174A40",fg=GREEN)
        self.status_var.set("Live simulated sensor stream started. New readings are saved to SQLite.")
        self.sim_thread=threading.Thread(target=self._simulation_worker,args=(active_stop_event,),name="climate-sensor-simulation",daemon=True)
        self.sim_thread.start()

    def stop_simulation(self):
        self.simulation_running=False;self.stop_event.set()
        if hasattr(self,"dashboard_start"):
            self.dashboard_start.configure(state="normal",text="▶  START LIVE SIMULATION")
        self.side_live.configure(text="●  STANDBY",fg=AMBER)
        self.sensor_caption.configure(text="Simulation paused",fg=MUTED)
        self.sensor_badge.configure(text="●  STANDBY",bg="#28394B",fg=AMBER)
        self.status_var.set("Simulation stopped. Existing observations remain saved.")

    def trigger_heatwave_event(self):
        """Insert a deterministic critical reading so the alert workflow is easy to demonstrate."""
        record = {
            "observed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "station": "Nagpur Heatwave Demo", "city": "Nagpur",
            "temperature": 41.6, "humidity": 29.0, "wind_speed": 7.5, "rainfall": 0.0,
            "condition_text": "Simulated heatwave event", "source": "Scenario simulation",
            "notes": "Synthetic demonstration event; not a live weather observation"
        }
        try:
            self.db.add(record)
            level = classify_alert(record["temperature"], record["humidity"], record["wind_speed"])
            self.current_reading = record
            self.chart_values.append(record["temperature"])
            self.chart_values = self.chart_values[-36:]
            self.alert_history.append({"time": datetime.now().strftime("%H:%M:%S"),
                "station": record["station"], "temperature": record["temperature"], "level": level})
            self.alert_history = self.alert_history[-30:]
            self.refresh_all()
            self.sensor_temp.configure(text=f'{record["temperature"]:.1f}°C')
            self.sensor_humidity.configure(text=f'HUMIDITY     {record["humidity"]:.0f}%')
            self.sensor_wind.configure(text=f'WIND              {record["wind_speed"]:.1f} km/h')
            self.sensor_station.configure(text=f'STATION        {record["station"]}')
            self.sensor_caption.configure(text="Synthetic critical event inserted", fg=RED)
            self.sensor_badge.configure(text="●  CRITICAL EVENT", fg=RED, bg="#482B3B")
            self.status_var.set("Demonstration event saved • 41.6°C • CRITICAL • synthetic data")
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not trigger scenario", str(exc))

    def _simulation_worker(self, stop_event):
        stations=[("Pune Central","Pune"),("Mumbai Coast","Mumbai"),("Nagpur East","Nagpur"),
                  ("Solapur North","Solapur"),("Nashik Station","Nashik"),("Aurangabad","Chhatrapati Sambhajinagar"),
                  ("Thane Urban","Thane"),("Kolhapur South","Kolhapur")]
        temp=random.uniform(35.5,39.0)
        while not stop_event.is_set():
            station,city=random.choice(stations)
            temp=max(31.0,min(43.0,temp+random.choice([-0.8,-0.4,0.1,0.3,0.7,1.1])+random.uniform(-0.5,0.5)))
            # Occasional hot spikes make warning behaviour demonstrable during a short presentation.
            if random.random()<0.12:temp=min(43.0,temp+random.uniform(1.5,3.0))
            humidity=round(random.uniform(27,82));wind=round(random.uniform(3,25),1);rain=random.choice([0,0,0,0.2,0.5])
            record={"observed_at":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"station":station,"city":city,
                    "temperature":round(temp,1),"humidity":humidity,"wind_speed":wind,"rainfall":rain,
                    "condition_text":"Simulated hot conditions","source":"Live simulation","notes":"Synthetic demonstration reading"}
            try:
                record_id=self.db.add(record)
                self.events.put(("reading",{"record":record,"id":record_id,"level":classify_alert(temp,humidity,wind)}))
            except Exception as exc:
                self.events.put(("error",str(exc)))
            stop_event.wait(2.0)

    def _poll_events(self):
        try:
            while True:
                kind,payload=self.events.get_nowait()
                if kind=="reading":
                    r=payload["record"];level=payload["level"]
                    self.current_reading=r;self.chart_values.append(float(r["temperature"]));self.chart_values=self.chart_values[-36:]
                    self.sensor_temp.configure(text=f'{r["temperature"]:.1f}°C')
                    self.sensor_humidity.configure(text=f'HUMIDITY     {r["humidity"]:.0f}%')
                    self.sensor_wind.configure(text=f'WIND              {r["wind_speed"]:.1f} km/h')
                    self.sensor_station.configure(text=f'STATION        {r["station"]}')
                    self.sensor_badge.configure(text=f'●  {level}',fg=ALERT_COLORS[level],
                        bg="#173A3A" if level=="NORMAL" else "#45391F" if level=="WARNING" else "#482B3B")
                    if level!="NORMAL":
                        self.alert_history.append({"time":datetime.now().strftime("%H:%M:%S"),"station":r["station"],"temperature":r["temperature"],"level":level})
                        self.alert_history=self.alert_history[-30:]
                    self.refresh_dashboard()
                    if self.page=="records":self.refresh_records()
                    if self.page=="analysis":self.refresh_analysis()
                    self.status_var.set(f'New simulated observation: {r["station"]} • {r["temperature"]:.1f}°C • {level}')
                elif kind=="monitor_done":
                    critical=[r for r in payload if r["alert_level"]=="CRITICAL"]
                    warning=[r for r in payload if r["alert_level"]=="WARNING"]
                    humidity_watch=[r for r in payload if r["humidity_status"]!="MODERATE"]
                    wind_watch=[r for r in payload if r["wind_status"]=="ELEVATED"]
                    self.status_var.set(f"Concurrent check complete • {len(payload):,} checked • {len(critical)} critical • {len(warning)} warning")
                    msg=f"Observations checked: {len(payload):,}\nCritical: {len(critical)}\nWarning: {len(warning)}\nNormal: {len(payload)-len(critical)-len(warning)}\n\nHumidity watch signals: {len(humidity_watch)}\nElevated wind signals: {len(wind_watch)}\n\nHumidity/wind labels are descriptive demo bands; alert severity is temperature-based."
                    messagebox.showinfo("Monitoring check complete",msg)
                elif kind=="error":
                    self.status_var.set("Simulation stopped after a storage error.")
                    messagebox.showerror("Simulation error",payload)
        except queue.Empty:pass
        if self.winfo_exists():self.after(120,self._poll_events)

    def run_monitor(self):
        rows=self.db.all()
        def worker():
            # Bounded worker pool demonstrates concurrency without spawning thousands of threads.
            from concurrent.futures import ThreadPoolExecutor
            def check(row):
                r=dict(row);r.update(monitor_conditions(r))
                return r
            with ThreadPoolExecutor(max_workers=8, thread_name_prefix="heat-check") as pool:
                result=list(pool.map(check, rows))
            self.events.put(("monitor_done",result))
        threading.Thread(target=worker,name="concurrent-climate-monitor",daemon=True).start()
        self.status_var.set("Concurrent monitoring check running in the background…")

    def _close(self):
        self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    ClimateApp().mainloop()
