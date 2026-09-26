"""Dependency-free mesoscopic queue model used to validate the research loop.

This is deliberately smaller than the planned SUMO/TraCI environment. Its job
is to make the hypotheses, controls, signals, conservation rules, and failure
criteria executable before the higher-fidelity adapter is introduced.
"""

from dataclasses import asdict, dataclass
from math import erf, exp, log, pi, sin, sqrt
import random
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Control:
    signal_offsets: Tuple[float, float]
    route_weights: Tuple[float, float, float]
    departure_delay: float

    def validate(self) -> None:
        if any(not 0.0 <= x <= 30.0 for x in self.signal_offsets):
            raise ValueError("signal offsets must be in [0, 30] seconds")
        if any(x < 0.0 for x in self.route_weights):
            raise ValueError("route weights must be non-negative")
        if abs(sum(self.route_weights) - 1.0) > 1e-8:
            raise ValueError("route weights must sum to one")
        if not 0.0 <= self.departure_delay <= 1.0:
            raise ValueError("departure delay must be in [0, 1]")


@dataclass(frozen=True)
class Metrics:
    demand: int
    seed: int
    completed: float
    completion_rate: float
    max_queue: float
    oscillation_index: float
    spillback: bool
    mean_speed: float
    conservation_error: float
    stable: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def no_intervention() -> Control:
    return Control((0.0, 0.0), (1.0, 0.0, 0.0), 0.0)


def reference_control() -> Control:
    """The mechanism-MVP control deliberately inserted as search trial 3."""
    return Control((8.0, 22.0), (0.34, 0.33, 0.33), 0.70)


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _cumulative_departures(t: float, demand: int, delay: float) -> float:
    if t <= 0:
        return 0.0
    if t >= 1500.0:
        return float(demand)
    median = 300.0 + 180.0 * delay
    sigma = 0.72
    z = (log(max(t, 1.0)) - log(median)) / sigma
    return demand * _normal_cdf(z)


def _effective_service_rate(control: Control) -> float:
    separation = abs(control.signal_offsets[1] - control.signal_offsets[0])
    coordination = exp(-abs(separation - 14.0) / 6.0)
    diversity = max(0.0, 1.0 - 1.5 * sum(abs(w - 1.0 / 3.0) for w in control.route_weights))
    departure_fit = max(0.0, 1.0 - abs(control.departure_delay - 0.40) / 0.60)
    return 0.48 + 0.15 * coordination + 0.12 * diversity + 0.05 * departure_fit


def _detrended_rms(series: List[float], demand: int) -> float:
    n = len(series)
    if n < 3 or max(series) <= 1e-9:
        return 0.0
    if max(series) < 0.40 * demand:
        return 0.0
    # Smooth the curve, classify meaningful slope direction, and count extra
    # reversals beyond the single rise-to-clear transition of a stable queue.
    smooth = []
    for i in range(n):
        window = series[max(0, i - 2):min(n, i + 3)]
        smooth.append(sum(window) / len(window))
    directions = []
    for i in range(1, n):
        delta = smooth[i] - smooth[i - 1]
        direction = 1 if delta > 0.25 else -1 if delta < -0.25 else 0
        if direction and (not directions or direction != directions[-1]):
            directions.append(direction)
    extra_reversals = max(0, len(directions) - 2)
    return extra_reversals / 20.0


def simulate(demand: int, control: Control, seed: int = 7, duration_s: int = 1800, step_s: int = 10) -> Tuple[Metrics, Dict[str, List[float]]]:
    control.validate()
    if demand <= 0:
        raise ValueError("demand must be positive")
    rng = random.Random(seed)
    rate = _effective_service_rate(control)
    queue = 0.0
    served = 0.0
    departed_prev = 0.0
    max_queue = 0.0
    queue_series: List[float] = []
    time_series: List[float] = []
    served_series: List[float] = []

    for t in range(step_s, duration_s + step_s, step_s):
        departed = _cumulative_departures(t, demand, control.departure_delay)
        arrivals = max(0.0, departed - departed_prev)
        departed_prev = departed
        queue += arrivals

        pressure = queue / max(0.30 * demand, 1.0)
        congestion = max(0.78, 1.0 - 0.18 * pressure)
        wave = 1.0
        if queue > 0.45 * demand:
            wave = 1.0 + 0.55 * sin(2.0 * pi * t / 120.0 + rng.random() * 0.08)
        service = min(queue, rate * step_s * congestion * wave)
        queue -= service
        served += service
        max_queue = max(max_queue, queue)

        # Every person is either not yet departed, queued, or served.
        not_departed = demand - departed
        conservation = not_departed + queue + served
        if abs(conservation - demand) > 1e-6:
            raise AssertionError("population conservation violated")

        time_series.append(float(t))
        queue_series.append(queue)
        served_series.append(served)

    completed = min(float(demand), served)
    completion_rate = completed / demand
    oscillation_index = _detrended_rms(queue_series, demand)
    spillback = max_queue >= 0.45 * demand
    mean_speed = max(0.18, 1.34 * (1.0 - 0.82 * max_queue / demand))
    stable = completion_rate >= 0.98 and not spillback and oscillation_index < 0.02
    metrics = Metrics(
        demand=demand,
        seed=seed,
        completed=round(completed, 6),
        completion_rate=round(completion_rate, 6),
        max_queue=round(max_queue, 6),
        oscillation_index=round(oscillation_index, 8),
        spillback=spillback,
        mean_speed=round(mean_speed, 6),
        conservation_error=0.0,
        stable=stable,
    )
    return metrics, {"time_s": time_series, "queue": queue_series, "served": served_series}
