#!/usr/bin/env python3
"""One-shot fixer: отсекает объявления 'куплю/cumpăr' в NotebookBuy."""
from pathlib import Path

SCORING_OLD = r'''# --- Fallback Tiers and Estimation Logic ---
MDL_USD_RATE = 18.0'''

SCORING_NEW = r'''_BUYING_AD_RE = re.compile(
    r"\b(?:куплю|скуплю|скупка|выкуп|cumpăr|cumpar|cumpărăm|cumparam)\b",
    re.IGNORECASE,
)

SHOP_SPAM_KEYWORDS = (
    "cele mai bune preturi",
    "cele mai bune prețuri",
    "pentru toate laptopurile",
    "asortiment",
)


def is_unwanted_ad(title: str, description: str = "") -> bool:
    """True for buying requests ('куплю/cumpăr') and shop spam, not real sales."""
    blob = f"{str(title or '').lower()} {str(description or '').lower()}"
    if _BUYING_AD_RE.search(blob):
        return True
    return any(kw in blob for kw in SHOP_SPAM_KEYWORDS)


# --- Fallback Tiers and Estimation Logic ---
MDL_USD_RATE = 18.0'''

ANALYZER_IMPORT_OLD = r'''    MIN_YEAR,
    score_laptop,'''
ANALYZER_IMPORT_NEW = r'''    MIN_YEAR,
    is_unwanted_ad,
    score_laptop,'''

ANALYZER_RUN_OLD = r'''                # Filter shop spam (both title and description)
                title_lower = title.lower()
                desc_lower = (desc or "").lower()
                shop_spam_keywords = ["cele mai bune preturi", "cele mai bune prețuri", "pentru toate laptopurile", "asortiment"]
                if any(kw in title_lower or kw in desc_lower for kw in shop_spam_keywords):
                    continue'''
ANALYZER_RUN_NEW = r'''                # Skip buying requests ("куплю/cumpăr") and shop spam
                if is_unwanted_ad(title, desc):
                    continue'''

DASH_IMPORT_OLD = r'''    classify_laptop,
    score_laptop,'''
DASH_IMPORT_NEW = r'''    classify_laptop,
    is_unwanted_ad,
    score_laptop,'''

DASH_QUERY_OLD = r'''            a.image_url,
            c.cpu,'''
DASH_QUERY_NEW = r'''            a.image_url,
            a.description,
            c.cpu,'''

DASH_FILTER_OLD = r'''unwanted_keywords = ["cumpar", "cumpăr", "куплю", "defect", "piese", "запчасти"]
shop_spam_keywords = ["cele mai bune preturi", "cele mai bune prețuri", "pentru toate laptopurile", "asortiment"]
def is_clean(title):
    title_lower = str(title).lower()
    if any(kw in title_lower for kw in unwanted_keywords):
        return False
    if any(kw in title_lower for kw in shop_spam_keywords):
        return False
    return True

df_raw = df_raw[df_raw['title'].apply(is_clean)]'''
DASH_FILTER_NEW = r'''parts_keywords = ["defect", "piese", "запчасти"]
def is_clean(row):
    if any(kw in str(row["title"]).lower() for kw in parts_keywords):
        return False
    return not is_unwanted_ad(row["title"], row.get("description", ""))

df_raw = df_raw[df_raw.apply(is_clean, axis=1)]'''

TG_IMPORT_OLD = r'''from scoring import MDL_USD_RATE, score_laptop'''
TG_IMPORT_NEW = r'''from scoring import MDL_USD_RATE, is_unwanted_ad, score_laptop'''

TG_PROC_OLD = r'''    unwanted_keywords = ["cumpar", "cumpăr", "куплю", "defect", "piese", "запчасти"]
    shop_spam_keywords = ["cele mai bune preturi", "cele mai bune prețuri", "pentru toate laptopurile", "asortiment"]
    deals = []

    for r in rows:
        title = r['title']
        title_lower = title.lower()
        if any(kw in title_lower for kw in unwanted_keywords):
            continue

        # Filter out shop spam from title
        if any(kw in title_lower for kw in shop_spam_keywords):
            continue'''
TG_PROC_NEW = r'''    parts_keywords = ["defect", "piese", "запчасти"]
    deals = []

    for r in rows:
        title = r['title']
        title_lower = title.lower()
        description = r['description'] if 'description' in r.keys() else ''
        if any(kw in title_lower for kw in parts_keywords):
            continue

        # Skip buying requests ("куплю/cumpăr") and shop spam
        if is_unwanted_ad(title, description):
            continue'''

EDITS = [
    ("scoring.py", SCORING_OLD, SCORING_NEW),
    ("laptop_analyzer_v3.py", ANALYZER_IMPORT_OLD, ANALYZER_IMPORT_NEW),
    ("laptop_analyzer_v3.py", ANALYZER_RUN_OLD, ANALYZER_RUN_NEW),
    ("laptop_dashboard.py", DASH_IMPORT_OLD, DASH_IMPORT_NEW),
    ("laptop_dashboard.py", DASH_QUERY_OLD, DASH_QUERY_NEW),
    ("laptop_dashboard.py", DASH_FILTER_OLD, DASH_FILTER_NEW),
    ("send_telegram.py", TG_IMPORT_OLD, TG_IMPORT_NEW),
    ("send_telegram.py", TG_PROC_OLD, TG_PROC_NEW),
]


def apply_edit(path: str, old: str, new: str) -> bool:
    text = Path(path).read_text(encoding="utf-8")
    if new in text:
        print(f"  = {path}: уже применено, пропуск")
        return True
    n = text.count(old)
    if n != 1:
        print(f"  ! {path}: якорь найден {n} раз (ожидался 1) — НЕ менял")
        return False
    Path(path).write_text(text.replace(old, new), encoding="utf-8")
    print(f"  + {path}: исправлено")
    return True


def main() -> None:
    ok = all(apply_edit(*e) for e in EDITS)
    print("\nГотово." if ok else "\nЧасть правок не применилась — см. строки с '!' выше.")


if __name__ == "__main__":
    main()