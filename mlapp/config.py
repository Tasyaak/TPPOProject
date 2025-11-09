from __future__ import annotations
from pathlib import Path
import yaml

def project_root() -> Path:
    # Корень проекта = каталог на уровень выше пакета mlapp/
    return Path(__file__).resolve().parents[1]

def default_config_path() -> Path:
    return project_root() / "configs" / "default.yaml"

def get_config(path: str | Path | None = None) -> dict:
    """Загружает YAML-конфиг и возвращает dict."""
    cfg_path = Path(path) if path else default_config_path()
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg or {}
