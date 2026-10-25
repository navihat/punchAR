"""Load the TOML config (all thresholds, durations, ports live there)."""
import tomllib
from pathlib import Path

from punchar.paths import CONFIG_PATH


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)
