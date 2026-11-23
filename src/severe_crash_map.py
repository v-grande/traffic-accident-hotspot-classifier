'''
Severe Crash Map

Displays a map of Philadelphia with a dot on every severe crash in the PennDOT 2025 data.

A crash is "severe" if FATAL_COUNT > 0 or SUSP_SERIOUS_INJ_COUNT > 0
    red dot    = at least one death
    orange dot = serious injury, no deaths

Output: outputs/severe_crash_map.html (opens in your web browser; zoom and pan,
click a dot for crash details). The map tiles load from Esri's public basemaps, so you
need an internet connection when viewing it.

Requires: pandas, folium
    pip install pandas folium
'''

import argparse
import webbrowser
from pathlib import Path

import folium
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "raw" / "CRASH_PHILADELPHIA_2025.csv"
OUT_FILE = ROOT / "outputs" / "severe_crash_map.html"

PHILLY_CENTER = (39.9526, -75.1652)
PHILLY_BOUNDS = {"lat": (39.85, 40.15), "lon": (-75.30, -74.93)}  # sanity box

DAY_NAMES = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}

# Same weather codes as hotspot_analysis.py -- verify against PennDOT's data dictionary
WEATHER = {
    1: "Blowing sand/dirt", 2: "Blowing snow", 3: "Clear", 4: "Cloudy",
    5: "Fog/smog/smoke", 6: "Freezing rain", 7: "Rain", 8: "Severe crosswinds",
    9: "Sleet/hail", 10: "Snow", 98: "Other", 99: "Unknown",
}

_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"
BASEMAPS = {  # first one is shown by default
    "Light gray map": f"{_ESRI}/Canvas/World_Light_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}",
    "Street map": f"{_ESRI}/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}",
    "Satellite": f"{_ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
}
ESRI_ATTR = "Tiles &copy; Esri"

COLORS = {"fatal": "#d62728", "serious": "#ff7f0e"}

NEEDED_COLS = ["CRN", "DEC_LATITUDE", "DEC_LONGITUDE", "HOUR_OF_DAY", "DAY_OF_WEEK",
               "WEATHER1", "FATAL_COUNT", "SUSP_SERIOUS_INJ_COUNT", "TOT_INJ_COUNT"]


def load_severe_crashes(csv_path):
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    missing = [c for c in NEEDED_COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"CSV is missing expected columns: {missing}")
    df = df[NEEDED_COLS].apply(pd.to_numeric, errors="coerce")
    df[["FATAL_COUNT", "SUSP_SERIOUS_INJ_COUNT", "TOT_INJ_COUNT"]] = (
        df[["FATAL_COUNT", "SUSP_SERIOUS_INJ_COUNT", "TOT_INJ_COUNT"]].fillna(0))
    n_all = len(df)

    # valid coordinates inside Philadelphia
    ok = (df["DEC_LATITUDE"].between(*PHILLY_BOUNDS["lat"])
          & df["DEC_LONGITUDE"].between(*PHILLY_BOUNDS["lon"]))
    df = df[ok]
    n_valid = len(df)

    severe = df[(df["FATAL_COUNT"] > 0) | (df["SUSP_SERIOUS_INJ_COUNT"] > 0)].copy()
    print(f"{n_all:,} crashes in file, {n_valid:,} with valid coordinates, "
          f"{len(severe):,} severe "
          f"({int((severe['FATAL_COUNT'] > 0).sum()):,} fatal, "
          f"{int((severe['FATAL_COUNT'] == 0).sum()):,} serious injury only).")
    return severe


def popup_text(r):
    hour = f"{int(r['HOUR_OF_DAY']):02d}:00" if 0 <= r["HOUR_OF_DAY"] <= 23 else "unknown"
    day = DAY_NAMES.get(r["DAY_OF_WEEK"], "unknown")
    weather = WEATHER.get(r["WEATHER1"], "unknown")
    return (f"<b>CRN {int(r['CRN'])}</b><br>"
            f"Deaths: {int(r['FATAL_COUNT'])}<br>"
            f"Serious injuries: {int(r['SUSP_SERIOUS_INJ_COUNT'])}<br>"
            f"Total injuries: {int(r['TOT_INJ_COUNT'])}<br>"
            f"{day} at {hour}<br>Weather: {weather}")


def build_map(severe):
    m = folium.Map(location=PHILLY_CENTER, zoom_start=12, tiles=None, control_scale=True)
    for i, (name, url) in enumerate(BASEMAPS.items()):
        folium.TileLayer(tiles=url, attr=ESRI_ATTR, name=name, max_zoom=19,
                         show=(i == 0)).add_to(m)

    layers = {
        "fatal": folium.FeatureGroup(name="Fatal crashes", show=True),
        "serious": folium.FeatureGroup(name="Serious injury crashes", show=True),
    }
    for _, r in severe.iterrows():
        kind = "fatal" if r["FATAL_COUNT"] > 0 else "serious"
        folium.CircleMarker(
            location=(r["DEC_LATITUDE"], r["DEC_LONGITUDE"]),
            radius=5 if kind == "fatal" else 4,
            color="black", weight=0.6,
            fill=True, fill_color=COLORS[kind], fill_opacity=0.85,
            popup=folium.Popup(popup_text(r), max_width=220),
        ).add_to(layers[kind])
    for layer in layers.values():
        layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    n_f = int((severe["FATAL_COUNT"] > 0).sum())
    legend = f"""
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                background: white; padding: 10px 14px; border: 1px solid #888;
                border-radius: 6px; font-size: 13px; font-family: sans-serif;">
      <b>Severe crashes, Philadelphia 2025</b><br>
      <span style="color:{COLORS['fatal']}; font-size:16px;">&#9679;</span> Fatal ({n_f:,})<br>
      <span style="color:{COLORS['serious']}; font-size:16px;">&#9679;</span>
      Serious injury ({len(severe) - n_f:,})<br>
      <i>Total: {len(severe):,}</i>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))

    # zoom to fit the data
    if len(severe):
        m.fit_bounds([[severe["DEC_LATITUDE"].min(), severe["DEC_LONGITUDE"].min()],
                      [severe["DEC_LATITUDE"].max(), severe["DEC_LONGITUDE"].max()]])
    return m


def main():
    ap = argparse.ArgumentParser(description="Map severe crashes in Philadelphia")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=OUT_FILE)
    ap.add_argument("--no-open", action="store_true", help="don't open the map in a browser")
    args = ap.parse_args()

    severe = load_severe_crashes(args.csv)
    if severe.empty:
        raise SystemExit("No severe crashes found.")

    m = build_map(severe)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(args.out))
    print(f"Saved map to {args.out}")
    if not args.no_open:
        webbrowser.open(args.out.resolve().as_uri())


if __name__ == "__main__":
    main()