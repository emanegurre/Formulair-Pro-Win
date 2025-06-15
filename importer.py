# importer.py ── CLI rápido
import argparse
from pathlib import Path
import services

parser = argparse.ArgumentParser(description="Importa CSV al sistema.")
parser.add_argument("csv", type=Path, help="Ruta del CSV de materias")
args = parser.parse_args()

res = services.import_materials_csv(args.csv)
print("Importación completada.", res)
