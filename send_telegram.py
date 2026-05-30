import json
import logging
import os
import re
import sqlite3
from datetime import datetime

import requests

# Import shared configurations and scoring
from app_config import DB_NAME, TELEGRAM_MIN_VALUE_SCORE, TELEGRAM_TOP_N
from estimation import estimate_fallback_price, estimate_fallback_score
from scoring import MDL_USD_RATE, infer_ssd_gb, is_unwanted_ad, score_laptop


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Retrieve tokens from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

WORLD_PRICE_CACHE = "pricehistory_cache.json"
NBC_CACHE_FILE = "notebookcheck_cache.json"
COMPONENTS_DB_FILE = "components_db.json"


def load_json_cache(filename):
    if os.path.exists(filename):
        try:
            with open(filename, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def extract_brand(title):
    title_lower = title.lower()
    brands = ["lenovo", "asus", "hp", "apple", "macbook", "dell", "acer", "msi", "gigabyte", "samsung", "huawei", "xiaomi", "microsoft", "razer", "toshiba", "sony"]
    for b in brands:
        if b in title_lower:
            return "Apple" if b in ("apple", "macbook") else b.upper()
    return "OTHER"

def extract_region(description):
    if not description:
        return "Молдова"
    m = re.search(r'\[region:\s*([^\]]+)\]', description, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        val_lower = val.lower()
        if "chișinău" in val_lower or "chisinau" in val_lower or "кишин" in val_lower:
            return "Кишинёв"
        elif "bălți" in val_lower or "balti" in val_lower or "бельц" in val_lower:
            return "Бельцы"
        return val

    # Fallback search in raw text
    desc_lower = description.lower()
    if "бельц" in desc_lower or "bălți" in desc_lower or "balti" in desc_lower or "бэлць" in desc_lower:
        return "Бельцы"
    if "кишин" in desc_lower or "chișinău" in desc_lower or "chisinau" in desc_lower:
        return "Кишинёв"
    return "Молдова"


def _get_runtime_ssd(r, brand, title_lower):
    is_apple = brand == 'Apple' or any(w in title_lower for w in ['apple', 'macbook'])
    year_est = r['year_est'] or (datetime.now().year - 7)
    return infer_ssd_gb(r['ssd'], year_est, is_apple)


def process_deals(rows, price_cache, nbc_cache, components_data):
    parts_keywords = ["defect", "piese", "запчасти"]
    deals = []

    for r in rows:
        title = r['title']
        title_lower = title.lower()
        description = r['description'] if 'description' in r.keys() else ''
        if any(kw in title_lower for kw in parts_keywords):
            continue

        # Skip buying requests ("куплю/cumpăr") and shop spam
        if is_unwanted_ad(title, description):
            continue

        brand = extract_brand(title)
        # Smart Normalization
        if any(w in title_lower for w in ['mackbook', 'macbook', 'apple', 'mac']):
            brand = 'Apple'

        # Score laptop
        score_res = score_laptop(
            cpu_score=r['cpu_score'],
            gpu_score=r['gpu_score'],
            ram=r['ram'],
            ssd=r['ssd'],
            year_est=r['year_est'],
            price=r['price'],
            is_broken=r['is_broken']
        )
        value_score = round(score_res.get("value_score", 0), 1)

        # vs World calculation
        ad_id_str = str(r['id'])
        vs_pct = 0.0
        vs_str = "—"

        # Check cache
        cache_data = price_cache.get(ad_id_str, {})
        world_price_usd = cache_data.get('current_usd')

        if not world_price_usd:
            # Fallback
            calc_price_mdl = estimate_fallback_price(r['cpu'], r['gpu'], r['ram'], r['ssd'], brand, components_data)
            if calc_price_mdl > 0:
                vs_pct = ((r['price'] - calc_price_mdl) / calc_price_mdl) * 100
                vs_str = f"{int(round(vs_pct))}%"
        else:
            world_price_mdl = world_price_usd * MDL_USD_RATE
            if world_price_mdl > 0:
                vs_pct = ((r['price'] - world_price_mdl) / world_price_mdl) * 100
                vs_str = f"{int(round(vs_pct))}%"

        # NBC Score
        nbc_data = nbc_cache.get(ad_id_str, {})
        nbc_score = nbc_data.get('score')
        if not nbc_score:
            nbc_score = estimate_fallback_score(r['cpu'], r['gpu'], r['ram'], components_data)

        # Risk assessment
        risk = ""
        if brand == 'Apple' and r['price'] < 12000 and any(chip in title_lower or chip in str(r['cpu']).lower() for chip in ['m2', 'm3', 'm4']):
            risk = "⚠️ Слишком низкая цена! Проверяйте на MDM профиль и iCloud!"
        elif brand == 'Apple' and vs_pct < -55:
            risk = "⚠️ Высокий (Скам/Блок)"
        elif brand != 'Apple' and vs_pct < -65:
            risk = "⚠️ Подозрительно дешево"
        elif r['price'] < 2000 and r['year_est'] > 2019:
            risk = "⚠️ На запчасти?"

        # Smart runtime SSD fallback for display/processing
        ssd_val = _get_runtime_ssd(r, brand, title_lower)

        # Optional quality floor (default 0 = keep all, rank later).
        if value_score >= TELEGRAM_MIN_VALUE_SCORE:
            deals.append({
                'title': title,
                'price': int(r['price']),
                'url': r['url'],
                'value_score': value_score,
                'vs_str': vs_str,
                'nbc_score': nbc_score,
                'cpu': r['cpu'],
                'ram': r['ram'],
                'ssd': ssd_val,
                'brand': brand,
                'risk': risk,
                'region': extract_region(r['description'] if 'description' in r.keys() else '')
            })
    return deals


def main():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.error("Telegram configuration missing. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return

    log.info("Connecting to database and calculating the best deals...")
    if not os.path.exists(DB_NAME):
        log.error("Database %s not found. Cannot send notifications.", DB_NAME)
        return

    # Load caches
    price_cache = load_json_cache(WORLD_PRICE_CACHE)
    nbc_cache = load_json_cache(NBC_CACHE_FILE)
    components_data = load_json_cache(COMPONENTS_DB_FILE)

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT a.id, a.title, a.price, a.url, a.description, c.cpu, c.gpu, c.ram, c.ssd, c.is_broken, c.year_est, c.cpu_score, c.gpu_score
        FROM ads a
        JOIN analysis_cache c ON a.id = c.id
    """
    rows = cursor.execute(query).fetchall()
    conn.close()

    deals = process_deals(rows, price_cache, nbc_cache, components_data)

    if not deals:
        log.info("No high-value laptop deals found today.")
        return

    # 1. Moldova deals (all regions) - Top N
    moldova_deals = sorted(deals, key=lambda x: x['value_score'], reverse=True)[:TELEGRAM_TOP_N]

    # 2. Balti deals - Top N
    balti_deals = [d for d in deals if d['region'] == "Бельцы"]
    balti_deals = sorted(balti_deals, key=lambda x: x['value_score'], reverse=True)[:TELEGRAM_TOP_N]

    # Format beautiful message
    message = "🔥 *ТОП ВЫГОДНЫХ НОУТБУКОВ 999.MD* 🔥\n"
    message += f"📅 _Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M')}_\n\n"

    # Moldova Section
    message += f"🌍 *ВСЯ МОЛДОВА (ТОП-{TELEGRAM_TOP_N})*\n"
    message += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    for idx, d in enumerate(moldova_deals, start=1):
        brand_emoji = "🍏" if d['brand'] == "Apple" else "💻"
        message += f"{idx}. {brand_emoji} *{d['title']}*\n"
        message += f" 📍 *Регион:* `{d['region']}`\n"
        message += f" 💰 *Цена:* {d['price']:,} MDL\n"
        message += f" 📈 *Выгода:* `{d['vs_str']} vs World`\n"
        message += f" 🎯 *NBC Score:* `{d['nbc_score']}%` | *Value Score:* `{d['value_score']}`\n"
        message += f" 🛠 *Характеристики:* `{d['cpu']} | {d['ram']}GB RAM | {d['ssd']}GB SSD`\n"
        if d.get('risk'):
            message += f" 🚨 *РИСК:* `{d['risk']}`\n"
        message += f" 🔗 [Открыть объявление]({d['url']})\n\n"

    # Balti Section
    message += f"\n🔔 *БЕЛЬЦЫ (ТОП-{TELEGRAM_TOP_N})*\n"
    message += "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
    if balti_deals:
        for idx, d in enumerate(balti_deals, start=1):
            brand_emoji = "🍏" if d['brand'] == "Apple" else "💻"
            message += f"{idx}. {brand_emoji} *{d['title']}*\n"
            message += f" 💰 *Цена:* {d['price']:,} MDL\n"
            message += f" 📈 *Выгода:* `{d['vs_str']} vs World`\n"
            message += f" 🎯 *NBC Score:* `{d['nbc_score']}%` | *Value Score:* `{d['value_score']}`\n"
            message += f" 🛠 *Характеристики:* `{d['cpu']} | {d['ram']}GB RAM | {d['ssd']}GB SSD`\n"
            if d.get('risk'):
                message += f" 🚨 *РИСК:* `{d['risk']}`\n"
            message += f" 🔗 [Открыть объявление]({d['url']})\n\n"
    else:
        message += "   _Выгодных предложений в Бельцах пока не найдено._\n\n"

    log.info("Sending message to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            log.info("Telegram notification sent successfully!")
        else:
            log.error("Failed to send message: %s", response.text)
    except Exception as e:
        log.error("Error sending Telegram message: %s", e)


if __name__ == "__main__":
    main()
