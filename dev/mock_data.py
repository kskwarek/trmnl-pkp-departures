"""Generate mock Larapaper data payloads shaped like the PKP PLK Open Data API.

    python dev/mock_data.py            -> dev/mock/*.json
    python dev/mock_data.py --big      -> also prints the payload size of a very busy station

Field names follow the /shortened variants in https://pdp-api.plk-sa.pl/swagger/v1/swagger.json.
"""

import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).parent / "mock"
TODAY = "2026-10-18"
STATION = 33019  # Kraków Główny

NAMES = {
    33019: "Kraków Główny", 33035: "Kraków Płaszów", 33605: "Warszawa Centralna",
    33506: "Warszawa Wschodnia", 34868: "Warszawa Zachodnia", 60001: "Gdynia Główna",
    60002: "Gdańsk Główny", 60003: "Przemyśl Główny", 60004: "Rzeszów Główny",
    60005: "Tarnów", 60006: "Zakopane", 60007: "Nowy Targ", 60008: "Katowice",
    60009: "Wrocław Główny", 60010: "Poznań Główny", 60011: "Szczecin Główny",
    60012: "Kraków Lotnisko", 60013: "Wieliczka Rynek-Kopalnia", 60014: "Oświęcim",
    60015: "Kielce", 60016: "Lublin Główny", 60017: "Bielsko-Biała Główna",
    60018: "Miechów", 60019: "Sędziszów", 60020: "Kraków Batowice", 60021: "Trzebinia",
}

# (planned departure at Kraków, category, carrier, number, destination, intermediate stops, extras)
TRAINS = [
    ("15:05", "IC", "IC", "3510", 33605, [60018, 60015], {}),
    ("16:12", "R", "PR", "33612", 60005, [33035], {}),
    ("16:40", "EIP", "IC", "1505", 33605, [60018], {}),
    ("17:02", "IC", "IC", "38170", 60003, [33035, 60005, 60004], {"live": {"ddm": 4, "ad": "2026-10-18T17:06:00"}}),
    ("17:10", "TLK", "IC", "53170", 60001, [60018, 33605, 60002], {"live": {"ddm": 25}}),
    ("17:18", "KS", "KS", "40630", 60008, [60021], {"live": {"ddm": 0}}),
    ("17:24", "SKA1", "KML", "18120", 60012, [], {"live": {"ddm": 2}}),
    ("17:31", "SKA4", "KML", "14512", 60013, [33035], {"cancel": True}),
    ("17:40", "IC", "IC", "6130", 60009, [60008], {"live": {"ddm": 12}, "toid": True}),
    ("17:47", "R", "PR", "33520", 60019, [60018], {}),
    ("17:55", "EIC", "IC", "5300", 60010, [60008, 60009], {"live": {"ddm": 0}}),
    ("18:05", "IC", "IC", "31104", 60006, [60007], {"name": "PODHALANIN"}),
    ("18:10", "R", "PR", "33622", 60005, [33035], {"technical": True}),
    ("18:20", "TLK", "IC", "83102", 60011, [60008, 60010], {}),
    ("18:34", "KS", "KS", "40632", 60017, [60021], {}),
    ("18:45", "EIP", "IC", "1513", 33605, [60018], {}),
    ("19:05", "R", "PR", "33524", 60014, [60021], {}),
    ("19:20", "IC", "IC", "14100", 60016, [60015], {}),
    ("23:58", "TLK", "IC", "38102", 60001, [60015, 33605], {"midnight": True}),
]


def stop(sid, ord_, arr=None, dep=None, platform="II", track="4", ady=0, ddy=0, number=None,
         category=None, stype="postój handlowy"):
    return {
        "id": sid, "ord": ord_,
        "acc": category if arr else None, "atn": number if arr else None,
        "apl": platform if arr else None, "atr": track if arr else None,
        "ady": ady, "atm": f"{arr}:00" if arr else None,
        "dcc": category if dep else None, "dtn": number if dep else None,
        "dpl": platform if dep else None, "dtr": track if dep else None,
        "ddy": ddy, "dtm": f"{dep}:00" if dep else None,
        "sti": 2 if "techn" in stype else 1, "stn": stype,
    }


def shift(hhmm, minutes):
    h, m = map(int, hhmm.split(":"))
    t = (h * 60 + m + minutes) % 1440
    return f"{t // 60:02d}:{t % 60:02d}"


def build_route(i, dep, cat, carrier, number, dest, via, extras, station=STATION):
    platforms = ["I", "II", "III", "IV", "V"]
    platform = platforms[i % len(platforms)]
    track = str(1 + (i * 3) % 9)
    origin = 60020 if dest != 60020 else 60021
    stops = [stop(origin, 1, dep=shift(dep, -15), number=number, category=cat, platform="1", track="1")]
    ddy = 1 if extras.get("midnight") else 0
    dep_here = shift(dep, 0)
    stops.append(stop(station, 2, arr=shift(dep, -3), dep=dep_here, platform=platform, track=track,
                      number=number, category=cat, ady=0, ddy=0,
                      stype="postój techniczny" if extras.get("technical") else "postój handlowy"))
    t = 0
    for k, sid in enumerate(via):
        t += 35
        stops.append(stop(sid, 3 + k, arr=shift(dep, t), dep=shift(dep, t + 2), number=number,
                          category=cat, ady=ddy if t > 0 and extras.get("midnight") else 0,
                          ddy=ddy if extras.get("midnight") else 0))
    stops.append(stop(dest, 3 + len(via), arr=shift(dep, t + 40), number=number, category=cat,
                      ady=1 if extras.get("midnight") else 0))
    oid = 170000 + i
    route = {
        "sid": 26, "oid": oid, "nm": extras.get("name"), "cc": carrier, "nn": number,
        "ian": None, "idn": None, "ccs": cat, "od": [TODAY], "st": stops, "cn": [],
    }
    if extras.get("toid"):
        route["toid"] = oid + 500000
    return route


def build_live(route, extras, station=STATION):
    my = next(s for s in route["st"] if s["id"] == station)
    live = extras.get("live")
    cancel = extras.get("cancel", False)
    if live is None and not cancel:
        return None
    ddm = (live or {}).get("ddm")
    departed = (live or {}).get("ad")
    st = []
    for s in route["st"]:
        # Like the real API: `ad` is a forecast (planned + delay) until the stop is confirmed (`cf`).
        forecast = f"{TODAY}T{shift(s['dtm'][:5], ddm or 0)}:00" if s["dtm"] else None
        st.append({
            "id": s["id"], "psn": s["ord"], "asn": s["ord"],
            "pa": f"{TODAY}T{s['atm']}" if s["atm"] else None,
            "pd": f"{TODAY}T{s['dtm']}" if s["dtm"] else None,
            "adm": ddm if s is my else None, "ddm": ddm if s is my else None,
            "aa": None, "ad": departed if (s is my and departed) else forecast,
            "cf": bool(s is my and departed), "cn": cancel,
        })
    return {
        "sid": route["sid"], "oid": route["oid"], "toid": route.get("toid"),
        "od": TODAY, "s": "X" if cancel else "P", "st": st,
    }


def board_payload():
    routes, live = [], []
    for i, (dep, cat, carrier, number, dest, via, extras) in enumerate(TRAINS):
        r = build_route(i, dep, cat, carrier, number, dest, via, extras)
        routes.append(r)
        op = build_live(r, extras)
        if op:
            live.append(op)
    # A train terminating at Kraków: must never appear as a departure.
    term = build_route(99, "17:35", "IC", "IC", "1600", 60004, [], {})
    term["st"] = [s for s in term["st"] if s["id"] != STATION]
    term["st"].append(stop(STATION, 9, arr="17:35"))
    routes.append(term)
    # Operations from yesterday's run of the same order must be ignored.
    stale = dict(live[0]) if live else None
    if stale:
        stale = {**stale, "od": "2026-10-17", "s": "C"}
        live.insert(0, stale)

    used = {s["id"] for r in routes for s in r["st"]}
    schedules = {
        "ts": f"{TODAY}T15:20:00Z",
        "pr": {"f": f"{TODAY}T00:00:00", "t": f"{TODAY}T00:00:00"},
        "rt": routes,
        "dc": {"st": {str(k): {"id": k, "nm": NAMES[k]} for k in sorted(used)},
               "cr": {"IC": "PKP Intercity S.A.", "PR": "POLREGIO S.A.", "KS": "Koleje Śląskie",
                      "KML": "Koleje Małopolskie"}},
    }
    operations = {
        "ts": f"{TODAY}T15:20:00Z",
        "pg": {"p": 1, "ps": 1000, "tc": len(live), "tp": 1, "hn": False, "hp": False},
        "tr": live,
        "st": {str(k): NAMES[k] for k in sorted(used)},
    }
    return {"IDX_0": schedules, "IDX_1": operations}


def lookup_payload():
    return {
        "generatedAt": f"{TODAY}T15:20:00Z",
        "stations": [
            {"id": 33019, "name": "Kraków Główny"}, {"id": 33035, "name": "Kraków Płaszów"},
            {"id": 60020, "name": "Kraków Batowice"}, {"id": 60012, "name": "Kraków Lotnisko"},
            {"id": 60022, "name": "Kraków Bieżanów"}, {"id": 60023, "name": "Kraków Business Park"},
        ],
        "totalCount": 6, "returnedCount": 6, "page": 1, "pageSize": 20, "totalPages": 1,
    }


def big_payload(routes=350, stops=25):
    """A very busy station: every route has `stops` full stops."""
    rnd = random.Random(1)
    rt = []
    for i in range(routes):
        st = [stop(70000 + rnd.randrange(3000), k, arr="12:00", dep="12:02", number="12345",
                   category="IC") for k in range(stops)]
        st[rnd.randrange(stops - 1)]["id"] = STATION
        rt.append({"sid": 26, "oid": i, "nm": None, "cc": "IC", "nn": "12345", "ian": None,
                   "idn": None, "ccs": "IC", "od": [TODAY], "st": st, "cn": []})
    names = {str(70000 + k): {"id": 70000 + k, "nm": "Stacja Przykładowa Główna"} for k in range(3000)}
    return {"IDX_0": {"ts": "", "pr": {"f": TODAY, "t": TODAY}, "rt": rt, "dc": {"st": names}},
            "IDX_1": {"tr": []}}


def pretty_size(payload):
    # Larapaper measures json_encode($payload, JSON_PRETTY_PRINT): 4-space indent, ASCII escapes.
    return len(json.dumps(payload, indent=4, ensure_ascii=True).encode())


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / "board.json").write_text(json.dumps(board_payload(), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "lookup.json").write_text(json.dumps(lookup_payload(), ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "lookup_empty.json").write_text(json.dumps({"stations": []}), encoding="utf-8")
    (OUT / "api_error.json").write_text(json.dumps({"IDX_0": {"error": "Failed to fetch data"},
                                                    "IDX_1": {"error": "Failed to fetch data"}}), encoding="utf-8")
    (OUT / "too_big.json").write_text(json.dumps({"error": "Data payload exceeds maximum allowed size"}), encoding="utf-8")
    (OUT / "empty_day.json").write_text(json.dumps({"IDX_0": {"pr": {"f": f"{TODAY}T00:00:00"}, "rt": [], "dc": {"st": {}}},
                                                    "IDX_1": {"tr": []}}), encoding="utf-8")
    if "--big" in sys.argv:
        for routes, stops in [(150, 20), (250, 20), (350, 25)]:
            print(f"{routes} routes x {stops} stops: {pretty_size(big_payload(routes, stops)) / 1e6:.1f} MB pretty-printed")
    print("wrote", sorted(p.name for p in OUT.iterdir()))
