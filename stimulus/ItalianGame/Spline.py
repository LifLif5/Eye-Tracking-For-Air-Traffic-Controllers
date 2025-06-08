import random
import math
import numpy as np
from scipy.interpolate import splprep, splev
from typing import Tuple, List

class Spline:
    def __init__(self, spline_points: List[Tuple[float, float]], arc_lengths: List[float]):
        self.spline_points = spline_points
        self.arc_lengths = arc_lengths
        self.total_length = arc_lengths[-1]
        self.distance_traveled = 0.0


    @classmethod
    def create(cls, start: Tuple[float, float], end: Tuple[float, float], seed=None) -> "Spline":
        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random

        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        dir_x, dir_y = dx / length, dy / length
        perp_x, perp_y = -dir_y, dir_x

        # Generate intermediate control points
        points = [start]
        for factor in [0.25, 0.5, 0.75]:
            px = start[0] + dx * factor + rng.uniform(-150, 150) * perp_x
            py = start[1] + dy * factor + rng.uniform(-150, 150) * perp_y
            points.append((px, py))
        points.append(end)

        x_vals, y_vals = zip(*points)
        spline_tck, _ = splprep([x_vals, y_vals], s=0)
        u_vals = np.linspace(0, 1, 200)
        x_samples, y_samples = splev(u_vals, spline_tck)
        spline_points = list(zip(x_samples, y_samples))

        arc_lengths = [0.0]
        for i in range(1, len(spline_points)):
            x0, y0 = spline_points[i - 1]
            x1, y1 = spline_points[i]
            arc_lengths.append(arc_lengths[-1] + math.hypot(x1 - x0, y1 - y0))

        return cls(spline_points, arc_lengths)

    def get_next(self, speed: float) -> Tuple[float, float]:
        self.distance_traveled += speed

        if self.distance_traveled >= self.total_length:
            return self.spline_points[-1]

        # Binary search to find segment
        low, high = 0, len(self.arc_lengths) - 1
        while low < high:
            mid = (low + high) // 2
            if self.arc_lengths[mid] < self.distance_traveled:
                low = mid + 1
            else:
                high = mid
        i = max(low - 1, 0)

        d0, d1 = self.arc_lengths[i], self.arc_lengths[i + 1]
        t = (self.distance_traveled - d0) / (d1 - d0)
        x0, y0 = self.spline_points[i]
        x1, y1 = self.spline_points[i + 1]
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t