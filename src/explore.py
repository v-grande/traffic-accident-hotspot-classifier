'''
Traffic Accident Hotspot Classifier 

Uses city accident data to find risky locations, times of day, and weather conditions.
Clusters accident locations or classify high-risk conditions.

Uses: dictionaries, CSV data, clustering, charts, engineering decision-making.
'''

import csv
from collections import Counter

path = "data/raw/CRASH_PHILADELPHIA_2025.csv"

with open(path, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    print("Columns:", reader.fieldnames)
    rows = list(reader)

print("Total crashes:", len(rows))
print("First row:", rows[0])