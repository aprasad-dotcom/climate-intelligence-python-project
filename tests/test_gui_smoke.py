"""Windows/Tk smoke coverage for page navigation and the demo workflows."""
import os
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ClimateGuiSmokeTests(unittest.TestCase):
    def test_navigation_simulation_and_heatwave_demo(self):
        import app as app_module

        temp_root = ROOT / "work" / "test-tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        original_db_path = app_module.DB_PATH
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            app_module.DB_PATH = os.path.join(folder, "gui_smoke.db")
            gui = app_module.ClimateApp()
            try:
                gui.withdraw()
                gui.update_idletasks()
                expected = {"dashboard", "records", "analysis", "predictions", "about"}
                self.assertEqual(set(gui.pages), expected)
                for key in sorted(expected):
                    gui.show_page(key)
                    gui.update_idletasks()
                    self.assertEqual(gui.pages[key].winfo_manager(), "pack")
                gui.geometry("880x580")
                gui.update_idletasks()

                initial_count = gui.db.count()
                gui.start_simulation()
                time.sleep(2.2)
                gui.update()
                gui.stop_simulation()
                gui.update()
                self.assertGreater(gui.db.count(), initial_count)

                gui.trigger_heatwave_event()
                demo = gui.db.all("Nagpur Heatwave Demo", limit=1)
                self.assertTrue(demo)
                self.assertEqual(demo[0]["temperature"], 41.6)
                self.assertEqual(demo[0]["alert_level"], "CRITICAL")
            finally:
                gui.stop_simulation()
                if hasattr(gui, "sim_thread"):
                    gui.sim_thread.join(timeout=1)
                gui.destroy()
                app_module.DB_PATH = original_db_path


if __name__ == "__main__":
    unittest.main(verbosity=2)
