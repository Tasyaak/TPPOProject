from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DB_DIR = PROJECT_ROOT / "db"
DB_SCRIPTS_DIR = DB_DIR / "scripts"
DB_PATH = DB_DIR / "app.db"
DB_SNAPSHOT_PATH = DB_DIR / "app.snapshot.db"
SCHEMA_SQL_PATH = DB_DIR / "schema.sql"
SEED_SQL_PATH = DB_DIR / "seed.sql"
TEMPLATES_YAML_PATH = DB_DIR / "templates.yaml"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
DEFAULT_CONFIG_PATH = NOTEBOOKS_DIR / "default.yaml"
PROCESSING_CPP_DIR = PROJECT_ROOT / "processing_cpp"
BUILD_DIR = PROCESSING_CPP_DIR / "build_tmp"
MODELS_DIR = PROJECT_ROOT / "models"
TEMP_OUTPUT_DIR = PROJECT_ROOT / "temp_output"
PARQUETS_DIR = NOTEBOOKS_DIR / "parquets"
CTX_JSONLS_DIR = NOTEBOOKS_DIR / "ctx_jsonls"