"""One-Euro filter for smoothing landmark coordinates while maintaining responsive motion.

Adaptive low-pass filter: smooths jitter when stationary, reacts instantly during fast movements.
"""
import math


class OneEuroFilter:
    """Adaptive low-pass filter designed for human motion jitter reduction."""

    def __init__(self, min_cutoff: float = 1.2, beta: float = 0.05, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = None
        self.dx_prev = 0.0
        self.t_prev = None

    def _alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, t_ms: float) -> float:
        if self.t_prev is None or self.x_prev is None:
            self.x_prev = x
            self.t_prev = t_ms
            return x
        dt = max((t_ms - self.t_prev) / 1000.0, 1e-4)
        self.t_prev = t_ms
        dx = (x - self.x_prev) / dt
        edx = self._alpha(self.d_cutoff, dt) * dx + (1.0 - self._alpha(self.d_cutoff, dt)) * self.dx_prev
        self.dx_prev = edx
        cutoff = self.min_cutoff + self.beta * abs(edx)
        alpha = self._alpha(cutoff, dt)
        self.x_prev = alpha * x + (1.0 - alpha) * self.x_prev
        return self.x_prev
