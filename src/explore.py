import csv
from collections import Counter

path = "data/raw/CRASH_PHILADELPHIA_2025.csv"

with open(path, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    print("Columns:", reader.fieldnames)
    rows = list(reader)

print("Total crashes:", len(rows))
print("First row:", rows[0])