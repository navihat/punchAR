"""[5] Metrics: per-stage latency with p50/p95/p99."""
import time
from collections import defaultdict
from contextlib import contextmanager

import numpy as np


class StageTimer:
    def __init__(self):
        self.samples = defaultdict(list)  # stage -> [ms]

    @contextmanager
    def stage(self, name):
        start = time.perf_counter()
        yield
        self.samples[name].append((time.perf_counter() - start) * 1000)

    def add(self, name, ms):
        self.samples[name].append(ms)

    def summary(self) -> str:
        lines = [f"{'stage':<14} {'n':>6} {'mean':>7} {'p50':>7} {'p95':>7} {'p99':>7}"]
        for name, v in self.samples.items():
            a = np.asarray(v)
            p50, p95, p99 = np.percentile(a, [50, 95, 99])
            lines.append(f"{name:<14} {len(a):>6} {a.mean():>7.1f} {p50:>7.1f} {p95:>7.1f} {p99:>7.1f}")
        return "\n".join(lines)
