"""Regression checks for CPU execution and physical constraints."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
HAS_CITY = importlib.util.find_spec("numpy") is not None and importlib.util.find_spec("torch") is not None

if HAS_CITY:
    import numpy as np
    import torch
    from pulse.demo import city_arrays
    from pulse.simulator.agent_swarm import AgentSwarm, SwarmConfig
    from pulse.simulator.block_routing import build_routing, NO_PATH
    from pulse.simulator.swarm_step import SwarmStepper
    from pulse.simulator.llm_leaders import LeaderTier


@unittest.skipUnless(HAS_CITY, "Install the city extra to test the city simulator")
class CityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_routing_preserves_disconnected_blocks(self):
        dist, pred = build_routing(
            np.array([[1, -1], [0, -1], [-1, -1]], dtype=np.int32),
            np.array([0.0, 100.0, 200.0]), np.zeros(3),
            np.array([0]), device="cpu", log=lambda _: None,
        )
        self.assertEqual(pred[0, 0], 0)
        self.assertEqual(pred[0, 1], 0)
        self.assertEqual(dist[0, 1], 100.0)
        self.assertEqual(pred[0, 2], NO_PATH)

    def test_cpu_profile_conserves_population_and_capacity(self):
        z = city_arrays()
        layer = SimpleNamespace(lon=z["lon"], lat=z["lat"], population=z["pop"], area_m2=z["area"])
        shelters = [SimpleNamespace(lon=x, lat=y, capacity=c)
                    for x, y, c in zip(z["s_lon"], z["s_lat"], z["s_cap"])]
        config = SwarmConfig(device="cpu", n_district=1, n_subdistrict=0, n_community=0,
                             n_grid=0, frac_knows_one=1.0, seed=7)
        swarm = AgentSwarm(layer, shelters, routing=None, config=config)
        swarm.depart_s.fill(0)
        dist, pred = build_routing(z["neigh"], z["lon"] * 111_320, z["lat"] * 110_540,
                                  np.arange(16), device="cpu", log=lambda _: None)
        stepper = SwarmStepper(swarm, device="cpu", neigh=z["neigh"], route_dist=dist,
                               route_pred=pred, event_buffer=4096)
        try:
            for _ in range(30):
                stepper.step(profile=True)
            totals = stepper.totals()
            self.assertEqual(totals["n_agents"], 1600)
            self.assertEqual(totals["accounted"], 1600)
            self.assertEqual(totals["conservation_error"], 0)
            self.assertEqual(totals["overfilled_shelters"], 0)
            self.assertGreater(totals["sheltered"], 0)
            self.assertLessEqual(totals["sheltered"], 960)
            self.assertTrue(stepper.timings)
        finally:
            stepper.finish()

    def test_invalid_leader_reply_cannot_change_belief(self):
        # Exercise the rejection path without a server or model weights.
        tier = LeaderTier.__new__(LeaderTier)
        tier.st = SimpleNamespace()
        tier.unparseable = tier.hallucinated = tier.applied = 0
        tier._apply([{"options": [1, 2]}], ['{"first": 999}'])
        tier._apply([{"options": [1, 2]}], ["unstructured reply"])
        self.assertEqual(tier.hallucinated, 1)
        self.assertEqual(tier.unparseable, 1)
        self.assertEqual(tier.applied, 0)


if __name__ == "__main__":
    unittest.main()
