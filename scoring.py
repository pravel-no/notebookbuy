"""
Shared laptop business logic.

Keep scoring, category rules, display normalization, and cache version here so
the analyzer, dashboard, and bundled app cannot drift apart.
"""
import datetime
import re


ANALYSIS_VERSION = "2026-05-18.1"


MIN_PRICE_MDL = 500
MAX_PRICE_MDL = 15000
MIN_YEAR = 2014
MIN_CPU_SCORE = 2500

RAM_MULT = {
    4: 0.6,
    6: 0.7,
    8: 0.8,
    12: 0.9,
    16: 1.0,
    24: 1.08,
    32: 1.15,
    48: 1.18,
    64: 1.2,
}

CATEGORY_EMOJI = {
    "Gaming": "[GAME]",
    "MacBook": "[MAC]",
    "Ultrabook": "[ULTRA]",
    "Office": "[OFFICE]",
}

CATEGORY_LABEL = {
    "Gaming": "GAMING",
    "MacBook": "MACBOOK",
    "Ultrabook": "ULTRABOOKS",
    "Office": "OFFICE",
}


def estimate_year_from_cpu(cpu_name: str) -> int | None:
    if not cpu_name:
        return None

    cpu_name = str(cpu_name).lower()

    intel_match = re.search(r"i[3579][-\s](\d{4,5})", cpu_name)
    if intel_match:
        model = intel_match.group(1)
        if len(model) == 5 or model.startswith(("10", "11")):
            gen = int(model[:2])
        elif len(model) == 4 and int(model[:2]) >= 12:
            gen = int(model[:2])
        else:
            gen = int(model[0])
        return 2010 + gen if gen < 10 else 2019 + (gen - 9)

    ultra_match = re.search(r"core\sultra\s[357]\s(\d{3})", cpu_name)
    if ultra_match:
        return 2024 if ultra_match.group(1).startswith("1") else 2025

    amd_match = re.search(r"ryzen\s[3579]\s(\d)", cpu_name)
    if amd_match:
        return 2016 + int(amd_match.group(1))

    for chip, year in {"m1": 2020, "m2": 2022, "m3": 2023, "m4": 2024}.items():
        if chip in cpu_name:
            return year

    if "snapdragon" in cpu_name:
        return 2024

    return None


def normalize_cpu_name(name: str, max_len: int = 25) -> str:
    if not name:
        return ""

    n = str(name).strip()
    if not n:
        return ""

    n_low = n.lower()
    if n[0].isupper() and len(n) > 6:
        return n[:max_len]
    if re.match(r"i[3579]-", n_low):
        return ("Core " + n.upper())[:max_len]
    if re.match(r"(ryzen|core ultra)", n_low):
        return n.title()[:max_len]
    return n[:max_len]


def classify_laptop(cpu: str, gpu_score: int, price: int | float) -> str:
    cpu_l = str(cpu or "").lower()
    gpu_score = gpu_score or 0
    price = price or 0

    if any(chip in cpu_l for chip in ("m1", "m2", "m3", "m4")):
        return "MacBook"
    if gpu_score > 6500:
        return "Gaming"
    if re.search(r"i[3579][-\s]\d{4,5}hx", cpu_l):
        return "Gaming"
    if re.search(r"\d{4}hs\b", cpu_l) and price > 10000:
        return "Gaming"
    if re.search(r"i[35][-\s]\d{4,5}[ug]\b", cpu_l):
        return "Office"
    if re.search(r"ryzen\s[35]\s\d{4}[ug]\b", cpu_l):
        return "Office"
    if gpu_score == 0 and price < 7000:
        return "Office"

    return "Ultrabook"


def score_laptop(
    cpu_score: int,
    gpu_score: int,
    ram: int,
    ssd: int,
    year_est: int | None,
    price: int | float,
    is_broken: bool,
) -> dict:
    """
    Returns dict with keys: value_score, tech_pts.
    value_score = performance-per-MDL index; higher means better value.
    tech_pts = hardware quality, ignoring price.
    """
    current_year = datetime.datetime.now().year

    cpu_val = cpu_score or 0
    gpu_val = gpu_score or 0
    ram = ram or 4
    ssd = ssd or 0
    year = year_est or (current_year - 5)

    ram_m = RAM_MULT.get(ram, 0.6 if ram < 8 else 1.2)
    ssd_bonus = min(ssd * 2, 4000)

    # Age penalty softened: 8% per year instead of 15%
    age = max(0, current_year - year)
    age_penalty = max(0.20, 1.0 - age * 0.08)

    broken_m = 0.1 if is_broken else 1.0

    tech_base = (cpu_val * 0.55) + (gpu_val * 0.35) + (ram * 150 + ssd_bonus) * 0.10
    tech_pts = tech_base * ram_m * age_penalty * broken_m
    value_score = (tech_pts / max(price or 0, 1)) * 100

    return {"value_score": value_score, "tech_pts": tech_pts}
