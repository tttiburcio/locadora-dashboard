import sys
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from main import _migrate_1to1_safe

print("Running 1:1 migration from manutencoes to ordens_servico...")
_migrate_1to1_safe()
print("Migration completed.")
