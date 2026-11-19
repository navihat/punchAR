"""Repo-level paths shared by all modules."""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT_DIR / "models" / "gesture_recognizer.task"
RESULTS_DIR = ROOT_DIR / "results"
DATA_DIR = ROOT_DIR / "data"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.toml"
