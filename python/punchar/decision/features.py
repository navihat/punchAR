"""Feature extraction and geometric calculations for MediaPipe 21 landmarks."""
import math
from typing import Dict, List, Optional, Tuple
import numpy as np


def extract_hand_features(landmarks_list) -> Dict:
    """Extract normalized 21-point hand features.

    - coords: 21x3 numpy array
    - hand_size: Euclidean distance between Landmark 0 (wrist) and Landmark 9 (middle MCP)
    - r_open: average distance of fingertips (8, 12, 16, 20) to wrist divided by hand_size
    - shape_vec: 63-dimensional translation- and scale-normalized vector
    """
    if hasattr(landmarks_list, "landmark"):
        coords = np.array([[lm.x, lm.y, lm.z] for lm in landmarks_list.landmark], dtype=np.float32)
    elif isinstance(landmarks_list, (list, tuple, np.ndarray)):
        coords = np.array(landmarks_list, dtype=np.float32)
    else:
        raise ValueError(f"Unsupported landmarks format: {type(landmarks_list)}")

    wrist = coords[0]
    palm = coords[9]

    in_bounds = bool(
        np.all(coords[:, 0] >= 0.01) and np.all(coords[:, 0] <= 0.99) and
        np.all(coords[:, 1] >= 0.01) and np.all(coords[:, 1] <= 0.99)
    )

    hand_size = float(np.linalg.norm(palm[:2] - wrist[:2])) + 1e-6
    tip_ids = [8, 12, 16, 20]
    tip_dists = [np.linalg.norm(coords[i][:2] - wrist[:2]) for i in tip_ids]
    r_open = float(np.mean(tip_dists) / hand_size)
    shape_vec = ((coords - wrist) / hand_size).flatten().astype(np.float32)

    return {
        "x": float(palm[0]),
        "y": float(palm[1]),
        "hand_size": hand_size,
        "r_open": r_open,
        "in_bounds": in_bounds,
        "shape_vec": shape_vec,
        "landmarks": coords,
    }


def get_corrected_handedness(raw_label: str, score: float, invert: bool = False) -> Tuple[str, float]:
    """Get standardized player-view handedness."""
    if invert:
        corrected = "Right" if raw_label == "Left" else "Left"
    else:
        corrected = raw_label
    return corrected, float(score)


def flatten_landmarks_21(landmarks_source) -> Optional[List[float]]:
    """Flatten 21 landmarks into a 63-float array [x0, y0, z0, ..., x20, y20, z20]."""
    if landmarks_source is None:
        return None

    flat: List[float] = []
    if hasattr(landmarks_source, "landmark"):
        pts = landmarks_source.landmark
        if len(pts) != 21:
            return None
        for p in pts:
            flat.extend([round(float(p.x), 4), round(float(p.y), 4), round(float(p.z), 4)])
        return flat

    if len(landmarks_source) != 21:
        return None
    for p in landmarks_source:
        flat.extend([round(float(p[0]), 4), round(float(p[1]), 4), round(float(p[2]), 4)])
    return flat
