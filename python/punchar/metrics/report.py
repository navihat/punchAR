"""Accuracy report: per-class precision/recall/F1 and confusion matrix."""
import numpy as np

from punchar.paths import RESULTS_DIR  # noqa: F401  (re-exported for tools)
from punchar.recognizer.mediapipe_recognizer import GESTURES


def build_report(gts, preds):
    labels = [g for g in GESTURES if g in set(gts) | set(preds)]
    idx = {g: i for i, g in enumerate(labels)}
    cm = np.zeros((len(labels), len(labels)), dtype=int)
    for g, p in zip(gts, preds):
        cm[idx[g], idx[p]] += 1

    lines = [f"Total samples: {len(gts)}",
             f"Overall accuracy: {np.trace(cm) / cm.sum():.2%}", "",
             f"{'class':<12} {'n':>5} {'precision':>9} {'recall':>7} {'f1':>6}"]
    for g in labels:
        i = idx[g]
        tp = cm[i, i]
        prec = tp / cm[:, i].sum() if cm[:, i].sum() else 0.0
        rec = tp / cm[i].sum() if cm[i].sum() else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        lines.append(f"{g:<12} {cm[i].sum():>5} {prec:>9.2%} {rec:>7.2%} {f1:>6.2f}")

    lines += ["", "Confusion matrix (rows = ground truth, cols = predicted):",
              " " * 12 + "".join(f"{g[:8]:>9}" for g in labels)]
    for g in labels:
        lines.append(f"{g:<12}" + "".join(f"{v:>9}" for v in cm[idx[g]]))
    return "\n".join(lines) + "\n"
