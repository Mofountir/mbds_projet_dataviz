from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "01_raw"
INTERMEDIATE_DIR = DATA_DIR / "02_intermediate"
PRIMARY_DIR = DATA_DIR / "03_primary"
