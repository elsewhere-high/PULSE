import json
import csv
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pulse.experiment import choose_best, run_all, run_search
from pulse.model import no_intervention, reference_control, simulate


class MechanismModelTests(unittest.TestCase):
    def test_deterministic_and_conservative(self):
        first, _ = simulate(1000, reference_control(), seed=7)
        second, _ = simulate(1000, reference_control(), seed=7)
        self.assertEqual(first, second)
        self.assertEqual(first.conservation_error, 0.0)

    def test_reference_improves_baseline(self):
        baseline, _ = simulate(1000, no_intervention(), seed=7)
        selected, _ = simulate(1000, reference_control(), seed=7)
        self.assertGreaterEqual(selected.completion_rate, baseline.completion_rate)
        self.assertLess(selected.oscillation_index, baseline.oscillation_index)
        self.assertFalse(selected.spillback)

    def test_expected_boundary_band(self):
        low, _ = simulate(1100, reference_control(), seed=7)
        high, _ = simulate(1300, reference_control(), seed=7)
        self.assertTrue(low.stable)
        self.assertFalse(high.stable)

    def test_trial_three_selected(self):
        self.assertEqual(choose_best(run_search())["trial"], 3)

    def test_evidence_export(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            run_all(output)
            data = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(data["candidate_boundary"], "1100-1300 vehicles")
            self.assertTrue((output / "demand_scan.csv").exists())
            self.assertEqual(data["project"], "PULSE")
            with (output / "queue_series.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertAlmostEqual(max(float(row["baseline_queue"]) for row in rows),
                                   data["baseline"]["max_queue"], places=5)
            self.assertAlmostEqual(max(float(row["selected_queue"]) for row in rows),
                                   data["best_trial"]["metrics"]["max_queue"], places=5)
            chart = ET.parse(output / "queue_response.svg")
            self.assertEqual(len(chart.findall(".//{http://www.w3.org/2000/svg}polyline")), 2)


if __name__ == "__main__":
    unittest.main()
