from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any 
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parent
DB_DIR = PROJECT_ROOT / "db"
DB_SCRIPTS_DIR = DB_DIR / "scripts"
DB_PATH = DB_DIR / "app.db"
SCHEMA_SQL_PATH = DB_DIR / "schema.sql"
SEED_SQL_PATH = DB_DIR / "seed.sql"
TEMPLATES_YAML_PATH = DB_DIR / "templates.yaml"
MLAPP_DIR = PROJECT_ROOT / "mlapp"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DEFAULT_CONFIG_PATH = NOTEBOOKS_DIR / "default.yaml"
PROCESSING_CPP_DIR = PROJECT_ROOT / "processing_cpp"
BUILD_DIR = PROCESSING_CPP_DIR / "build_tmp"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_SAVE_PATTERN = "{ts}/{model_name}"
TEMP_OUTPUT_DIR = PROJECT_ROOT / "temp_output"
PARQUETS_DIR = NOTEBOOKS_DIR / "parquets"
CTX_JSONLS_DIR = NOTEBOOKS_DIR / "ctx_jsonls"


def load_config(path : str | Path | None = None) -> dict[str, Any]:
    """Читает YAML (по умолчанию notebooks/default.yaml) и возвращает dict"""
    cfg_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise TypeError(f"Top-level config in {cfg_path} must be a mapping (dict)")
    return cfg


def get_model_save_dir(model_name : str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    subdir = MODELS_SAVE_PATTERN.format(ts, model_name)
    return MODELS_DIR / subdir