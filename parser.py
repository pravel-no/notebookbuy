"""Regex-based hardware spec extraction from laptop ad text.

Precompiles patterns for CPU, GPU, RAM, and SSD at import time so
``LaptopParser.regex_parse`` runs fast even on large batches.
"""

import re
from typing import Any

from scoring import classify_laptop, estimate_year_from_cpu, normalize_cpu_name


# Precompiled regular expressions for performance
CPU_REGEX = re.compile(
    r'\b('
    r'i[3579][-\s]\d{4,5}[hxugt]{0,3}'            # Intel Core i7-12700H, i5-1135G7
    r'|core\s+ultra\s+[3579]\s+\d{3,5}[hxug]?'     # Intel Core Ultra 7 155H
    r'|ryzen\s+[3579]\s+\d{4}[hxusg]{0,3}'         # AMD Ryzen 7 5800H
    r'|snapdragon\s*(?:x|8[a-z0-9]*)'              # Snapdragon X Elite, 8cx
    r'|m[1234]\s*(?:pro|max|ultra)?'               # Apple M1, M2 Pro, M3 Max (will be post-processed for brand)
    r'|celeron\s*(?:gold|silver)?\s*[a-z0-9]+'     # Intel Celeron N4020
    r'|pentium\s*(?:gold|silver)?\s*[a-z0-9]+'     # Intel Pentium Gold 7505
    r'|xeon\s*[a-z0-9-]+'                          # Intel Xeon E3-1535M
    r'|athlon\s*(?:gold|silver)?\s*[a-z0-9]+'      # AMD Athlon Gold 3150U
    r'|i[3579](?!\d)'                              # Generic Intel Core i3/i5/i7/i9
    r')\b'
)

GPU_REGEX = re.compile(
    r'\b('
    r'rtx\s*\d{3,4}(?:\s*ti)?'                     # NVIDIA RTX 3060, 4070 Ti
    r'|gtx\s*\d{3,4}(?:\s*ti)?'                    # NVIDIA GTX 1650
    r'|rx\s*\d{3,4}(?:\s*xt)?'                     # AMD RX 6600 XT
    r'|radeon\s+(?:\d{3,4}m?|pro|graphics|graphics\s+\d+|780m|680m)' # AMD Radeon
    r'|geforce\s+mx\s*\d{3}'                       # NVIDIA MX350, MX450
    r'|iris\s+xe'                                  # Intel Iris Xe
    r'|intel\s+(?:uhd|hd)\s*(?:graphics)?\s*\d*'   # Intel UHD/HD Graphics
    r')\b'
)

RAM_REGEX = re.compile(r'\b(4|6|8|12|16|24|32|48|64|128)\s*(?:gb|гб|g)\b')
SSD_REGEX = re.compile(r'\b(128|256|500|512|1000|1024|2000|2048|1|2|4)\s*(?:tb|тб|gb|гб|t|g)?\s*(?:ssd|nvme|hdd|ссд|m\.2|pcie)\b')
YEAR_REGEX = re.compile(r'\b(20(?:0[8-9]|1[0-9]|2[0-5]))\b') # Years from 2008 to 2025


class LaptopParser:
    @staticmethod
    def estimate_year(cpu_name: str) -> int | None:
        return estimate_year_from_cpu(cpu_name)

    @staticmethod
    def normalize_cpu(name: str) -> str:
        return normalize_cpu_name(name)

    @staticmethod
    def classify(cpu: str, gpu_score: int, price: int) -> str:
        return classify_laptop(cpu, gpu_score, price)

    @staticmethod
    def regex_parse(text: str, title: str) -> dict[str, Any]:
        full_text = f"{title} {text}".lower()

        cpu_match = CPU_REGEX.search(full_text)
        gpu_match = GPU_REGEX.search(full_text)
        ram_match = RAM_REGEX.search(full_text)
        ssd_match = SSD_REGEX.search(full_text)
        year_match = YEAR_REGEX.search(full_text) # Search for explicit year

        cpu = cpu_match.group(0).strip() if cpu_match else ""

        # Post-processing for Apple M-series to prevent hallucinations
        if re.search(r'm[1234]', cpu, re.IGNORECASE): # If an M-series CPU was detected
            # Check if "apple" or "macbook" is present in the full text
            if not re.search(r'(?:apple|macbook)', full_text):
                cpu = "" # Discard the M-series CPU match if not an Apple product

        # Robust SSD Size Extraction
        ssd_match = None

        # 1. Standard pattern with SSD/NVMe label:
        # e.g., "256gb ssd", "256 ssd", "1tb nvme", "1 tb ssd"
        pattern_labeled = re.compile(
            r'\b(128|256|500|512|1000|1024|2000|2048|1|2|4)\s*(?:tb|тб|gb|гб|t|g)?\s*(?:ssd|nvme|hdd|ссд|m\.2|pcie)\b',
            re.IGNORECASE
        )
        ssd_match = pattern_labeled.search(full_text)

        # 2. Standalone TB pattern (since RAM is never in TB):
        # e.g., "1tb", "2 tb", "1t"
        if not ssd_match:
            pattern_tb = re.compile(r'\b(1|2|4)\s*(?:tb|тб|t)\b', re.IGNORECASE)
            ssd_match = pattern_tb.search(full_text)

        # 3. Standalone large GB pattern (256GB and above are always SSD, not RAM):
        # e.g., "256gb", "512 gb", "256g"
        if not ssd_match:
            pattern_large_gb = re.compile(r'\b(256|500|512|1000|1024|2000|2048)\s*(?:gb|гб|g)\b', re.IGNORECASE)
            ssd_match = pattern_large_gb.search(full_text)

        # 4. If we still don't have a match, let's search for "128gb" if it's not already matched by RAM_REGEX
        # e.g. "8gb 128gb" where 8gb is RAM, so 128gb is SSD
        if not ssd_match:
            pattern_128gb = re.compile(r'\b128\s*(?:gb|гб|g)\b', re.IGNORECASE)
            m_128 = pattern_128gb.search(full_text)
            if m_128:
                ram_val = int(ram_match.group(1)) if ram_match else 0
                if ram_val != 128:
                    ssd_match = m_128

        # Format/Clean SSD size
        ssd_val = 0
        if ssd_match:
            try:
                matched_str = ssd_match.group(0)
                num_str = re.search(r'\d+', matched_str).group(0)
                num = int(num_str)
                unit_match = re.search(r'(tb|тб|gb|гб|t|g)', matched_str)
                unit = unit_match.group(1) if unit_match else None

                if unit in ('tb', 'тб', 't') or (num in (1, 2, 4) and not unit):
                    ssd_val = num * 1024
                elif unit in ('gb', 'гб', 'g'):
                    ssd_val = num
                elif num in (1, 2, 4): # fallback assume TB if number is very small
                    ssd_val = num * 1024
                else: # Fallback for numbers without clear units, assume GB if reasonable
                    if num > 10 and num < 4000:
                        ssd_val = num
                    elif num <= 4:
                        ssd_val = num * 1024
            except Exception:
                ssd_val = 0

        year_est = None
        if year_match:
            year_est = int(year_match.group(1))
        else:
            year_est = LaptopParser.estimate_year(cpu) # Fallback to CPU-based estimation

        return {
            "cpu": cpu,
            "gpu": gpu_match.group(0).strip() if gpu_match else "integrated",
            "ram": int(ram_match.group(1)) if ram_match else 0,
            "ssd": ssd_val,
            "is_broken": any(k in full_text for k in [
                "запчаст", "дефект", "не работ", "разбит экран", "треснут экран", "битый экран", "экран не работ",
                "не включ", "schimb", "piese", "defect", "parola", "blocat", "заблокирован", "на запчасти",
                "без торга", "срочно", "продам срочно", "urgent"
            ]),
            "year_est": year_est
        }
