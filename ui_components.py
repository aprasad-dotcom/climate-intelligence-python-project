"""Reusable, responsive Tkinter UI components; no external GUI framework required."""
import math
import tkinter as tk
from theme import BG, PANEL, PANEL_ALT, PANEL_HOVER, BORDER, TEXT, MUTED, DIM, CYAN, BLUE, GREEN, AMBER, RED, PURPLE, ORANGE, ALERT_COLORS, FONT


class ScrollableFrame(tk.Frame):
    """Canvas-backed vertical scrolling. Mouse wheel works over the workspace and its children."""
    def __init__(self, master, bg=BG, **kwargs):
        super().__init__(master, bg=bg, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                      bg=PANEL_ALT, troughcolor=BG, activebackground=CYAN,
                                      relief="flat", bd=0, width=12)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.bind("<Configure>", self._resize_inner)
        self.canvas.bind_all("<MouseWheel>", self._wheel_windows, add="+")
        self.canvas.bind_all("<Button-4>", self._wheel_linux, add="+")
        self.canvas.bind_all("<Button-5>", self._wheel_linux, add="+")

    def _update_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _is_descendant(self, widget, parent):
        current = widget
        while current is not None:
            if current == parent:
                return True
            current = getattr(current, "master", None)
        return False

    def _over_inner_scrollable(self, widget):
        current = widget
        while current is not None and current != self:
            # Treeview/Listbox have their own scrolling behaviour. Text widgets in this
            # app intentionally let the outer workspace scroll when the pointer is over them.
            if isinstance(current, tk.Listbox) or current.winfo_class() in ("Treeview", "Listbox"):
                return True
            current = getattr(current, "master", None)
        return False

    def _wheel_windows(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget and self._is_descendant(widget, self) and not self._over_inner_scrollable(widget):
                units = max(1, round(abs(event.delta) / 120))
                self.canvas.yview_scroll(-units if event.delta > 0 else units, "units")
        except tk.TclError:
            pass

    def _wheel_linux(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget and self._is_descendant(widget, self) and not self._over_inner_scrollable(widget):
                self.canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        except tk.TclError:
            pass

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)


class Panel(tk.Frame):
    def __init__(self, master, bg=PANEL, **kwargs):
        super().__init__(master, bg=bg, highlightbackground=BORDER, highlightthickness=1, **kwargs)


class ActionButton(tk.Button):
    def __init__(self, master, text, command, variant="secondary", compact=False, **kwargs):
        styles = {
            "primary": (CYAN, "#06202A", CYAN),
            "secondary": (PANEL_ALT, TEXT, PANEL_HOVER),
            "blue": ("#183C5B", BLUE, "#214E73"),
            "danger": ("#452638", "#FFD9E0", "#633046"),
            "quiet": (PANEL, MUTED, PANEL_ALT),
            "green": ("#173D37", GREEN, "#20544B"),
        }
        bg, fg, active = styles.get(variant, styles["secondary"])
        super().__init__(master, text=text, command=command, bg=bg, fg=fg,
                         activebackground=active, activeforeground=fg, relief="flat", bd=0,
                         cursor="hand2", font=(FONT, 9 if compact else 10, "bold"),
                         padx=12 if compact else 16, pady=7 if compact else 11,
                         highlightthickness=0, **kwargs)


class MetricCard(Panel):
    def __init__(self, master, title, value, subtitle, accent, icon="●"):
        super().__init__(master, bg=PANEL)
        self.accent = accent
        tk.Frame(self, bg=accent, height=3).pack(fill="x")
        top = tk.Frame(self, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(12, 3))
        tk.Label(top, text=icon, bg=PANEL, fg=accent, font=(FONT, 12, "bold")).pack(side="left")
        tk.Label(top, text=title.upper(), bg=PANEL, fg=MUTED, font=(FONT, 8, "bold")).pack(side="left", padx=8)
        self.value_label = tk.Label(self, text=value, bg=PANEL, fg=TEXT, font=(FONT, 23, "bold"), anchor="w")
        self.value_label.pack(fill="x", padx=14, pady=(1, 1))
        self.subtitle_label = tk.Label(self, text=subtitle, bg=PANEL, fg=accent, font=(FONT, 8), anchor="w")
        self.subtitle_label.pack(fill="x", padx=14, pady=(2, 13))

    def set_value(self, value, subtitle=None):
        self.value_label.configure(text=value)
        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)


class TemperatureChart(tk.Canvas):
    def __init__(self, master, height=250, **kwargs):
        super().__init__(master, bg=PANEL, height=height, highlightthickness=0, bd=0, **kwargs)
        self.values = []
        self.bind("<Configure>", lambda _e: self.draw())

    def set_values(self, values):
        self.values = [float(v) for v in values[-36:]]
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = max(self.winfo_width(), 360), max(self.winfo_height(), 170)
        left, right, top, bottom = 42, 20, 18, 28
        pw, ph = w-left-right, h-top-bottom
        low, high = 20.0, 45.0
        def yy(v): return top + (high-v)/(high-low)*ph
        for temp in (20,25,30,35,40,45):
            y=yy(temp)
            self.create_line(left,y,w-right,y,fill="#20354A",dash=(2,5))
            self.create_text(left-10,y,text=str(temp),fill=MUTED,font=(FONT,8),anchor="e")
        for temp, color, label in ((37,AMBER,"WARNING"),(40,RED,"CRITICAL")):
            y=yy(temp)
            self.create_line(left,y,w-right,y,fill=color,dash=(7,5),width=1)
            self.create_text(w-right-2,y-8,text=label,fill=color,font=(FONT,7,"bold"),anchor="e")
        vals=self.values[-36:]
        if vals:
            pts=[]
            for i,v in enumerate(vals):
                x=left + pw*i/max(1,len(vals)-1)
                pts.extend((x,yy(min(high,max(low,v)))))
            if len(vals)>1:
                self.create_line(*pts,fill=CYAN,width=2,smooth=True,splinesteps=16)
                # translucent-looking area fill built from a polygon.
                area = pts[:] + [left+pw, top+ph, left, top+ph]
                self.create_polygon(*area, fill="#102B3B", outline="", stipple="gray50")
                self.tag_lower("all")
                self.create_line(*pts,fill=CYAN,width=2,smooth=True,splinesteps=16)
            for i,v in enumerate(vals):
                x=left + pw*i/max(1,len(vals)-1); y=yy(min(high,max(low,v)))
                color=RED if v>=40 else AMBER if v>=37 else CYAN
                self.create_oval(x-3,y-3,x+3,y+3,fill=color,outline=PANEL,width=1)
        self.create_text(left,h-9,text="EARLIER",fill=MUTED,font=(FONT,8),anchor="w")
        self.create_text(w-right,h-9,text="LATEST",fill=MUTED,font=(FONT,8),anchor="e")


class HeatMapCanvas(tk.Canvas):
    """Stylized regional monitoring map built from Canvas shapes (no internet/API required)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#0A1B2A", highlightthickness=0, bd=0, **kwargs)
        self.stations = []
        self.phase = 0
        self.bind("<Configure>", lambda _e: self.draw())

    def set_stations(self, stations):
        self.stations = stations[:12]
        self.draw()

    def draw(self):
        self.delete("all")
        w,h=max(360,self.winfo_width()),max(230,self.winfo_height())
        # faint grid / longitude and latitude guides
        for x in range(0,w,36): self.create_line(x,0,x,h,fill="#142C3D")
        for y in range(0,h,30): self.create_line(0,y,w,y,fill="#142C3D")
        # abstract regional coast/terrain contours, intentionally illustrative
        contours = [
            [(0,.23),(.13,.18),(.24,.25),(.31,.39),(.43,.35),(.54,.43),(.62,.33),(.76,.36),(.86,.27),(1,.31)],
            [(0,.38),(.14,.34),(.22,.42),(.35,.48),(.45,.44),(.57,.54),(.69,.47),(.81,.5),(.92,.42),(1,.45)],
            [(0,.58),(.12,.52),(.24,.61),(.34,.65),(.48,.6),(.59,.71),(.7,.64),(.84,.67),(1,.58)],
            [(.06,.8),(.19,.73),(.3,.8),(.42,.77),(.54,.85),(.68,.78),(.8,.82),(.96,.74)]
        ]
        for line in contours:
            coords=[]
            for x,y in line: coords.extend((x*w,y*h))
            self.create_line(*coords,fill="#24485A",width=1,smooth=True)
        # warm/cool zones drawn as layered transparent-looking ovals
        blobs=[(.35,.53,AMBER,1.0),(.64,.43,RED,.85),(.79,.63,ORANGE,.7),(.52,.72,BLUE,.55)]
        for bx,by,color,strength in blobs:
            radius=min(w,h)*(.15*strength)
            for scale, col in [(1.0,"#173847"),(.75,"#244B51"),(.48,"#6A4936"),(.25,color)]:
                r=radius*scale
                self.create_oval(bx*w-r,by*h-r,bx*w+r,by*h+r,fill=col,outline="")
        # faint route lines between station points
        points=[(.16,.44),(.32,.36),(.4,.58),(.56,.43),(.68,.55),(.83,.38),(.76,.75),(.24,.72)]
        route=[]
        for x,y in points: route.extend((x*w,y*h))
        self.create_line(*route,fill="#4B778A",width=1,dash=(3,5),smooth=True)
        station_names=self.stations or [
            {"station":"Pune Central","temperature":35.2,"alert_level":"NORMAL"},
            {"station":"Nagpur East","temperature":38.2,"alert_level":"WARNING"},
            {"station":"Solapur North","temperature":39.1,"alert_level":"WARNING"},
            {"station":"Mumbai Coast","temperature":34.1,"alert_level":"NORMAL"},
            {"station":"Nashik Station","temperature":36.1,"alert_level":"NORMAL"},
        ]
        coords=[(.16,.44),(.32,.36),(.4,.58),(.56,.43),(.68,.55),(.83,.38),(.76,.75),(.24,.72),(.51,.27),(.9,.65),(.1,.61),(.62,.8)]
        for i,station in enumerate(station_names[:len(coords)]):
            x,y=coords[i]; temp=float(station.get("temperature",30)); level=station.get("alert_level","NORMAL")
            col=ALERT_COLORS.get(level,CYAN); px,py=x*w,y*h
            self.create_oval(px-9,py-9,px+9,py+9,outline=col,width=1)
            self.create_oval(px-4,py-4,px+4,py+4,fill=col,outline="")
            if i%2==0 or level!="NORMAL":
                name=station.get("station",f"Station {i+1}")
                self.create_text(px+10,py-10,text=f"{name}  {temp:.1f}°",fill="#D9EAF7",font=(FONT,7,"bold"),anchor="w")
        self.create_text(14,14,text="WESTERN INDIA  /  STATION NETWORK",fill="#8BAEC1",font=(FONT,8,"bold"),anchor="nw")
        self.create_text(w-14,h-13,text="ILLUSTRATIVE MONITORING MAP",fill="#5B8197",font=(FONT,7),anchor="se")
