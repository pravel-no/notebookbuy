"""Tests for regex-based hardware spec extraction."""
import pytest

from parser import LaptopParser


@pytest.mark.parametrize(
    "title,text,expected_cpu,expected_gpu,expected_ram,expected_ssd,expected_broken",
    [
        (
            "Lenovo Legion 5",
            "Игровой ноутбук с RTX 3060, Ryzen 7 5800H, 16gb гб ram, 512gb ssd. В идеале.",
            "ryzen 7 5800h",
            "rtx 3060",
            16,
            512,
            False,
        ),
        (
            "Macbook Air 13 M1",
            "Продаю макбук м1 8гб озу 256 gb ssd nvme",
            "m1",
            "integrated",
            8,
            256,
            False,
        ),
        (
            "HP Pavilion",
            "Ноутбук Celeron N4020 4GB RAM 128GB SSD. Треснут экран, на запчасти",
            "celeron n4020",
            "integrated",
            4,
            128,
            True,
        ),
        (
            "Samsung 750XED - i5 1235u",
            "Шустрый i5 1235u, 8gb ram, 512 ssd",
            "i5 1235u",
            "integrated",
            8,
            512,
            False,
        ),
        (
            "Asus Vivobook",
            "Intel Pentium Gold 7505, Intel UHD Graphics, 16 gb ram, 1tb hdd",
            "pentium gold 7505",
            "intel uhd graphics",
            16,
            1024,
            False,
        ),
    ],
)
def test_regex_parse(
    title: str,
    text: str,
    expected_cpu: str,
    expected_gpu: str,
    expected_ram: int,
    expected_ssd: int,
    expected_broken: bool,
) -> None:
    res = LaptopParser.regex_parse(text, title)
    assert res["cpu"] == expected_cpu
    assert res["gpu"] == expected_gpu
    assert res["ram"] == expected_ram
    assert res["ssd"] == expected_ssd
    assert res["is_broken"] == expected_broken


# --- Edge cases ---

def test_empty_strings_return_defaults():
    res = LaptopParser.regex_parse("", "")
    assert res["cpu"] == ""
    assert res["gpu"] == "integrated"
    assert res["ram"] == 0
    assert res["ssd"] == 0
    assert res["is_broken"] is False


def test_gpu_only_no_cpu():
    res = LaptopParser.regex_parse("Видеокарта RTX 4060 ti, 16 gb", "Gaming laptop")
    assert res["gpu"] == "rtx 4060 ti"
    assert res["cpu"] == ""  # no CPU in text


def test_tb_ssd_units():
    res = LaptopParser.regex_parse("2tb ssd nvme", "Workstation")
    assert res["ssd"] == 2048


def test_one_gb_ssd_not_treated_as_terabyte():
    res = LaptopParser.regex_parse("1 gb ssd", "Budget laptop")
    assert res["ssd"] == 1


def test_n_series_cpu():
    res = LaptopParser.regex_parse("Intel Celeron N5030 4gb ram 64gb ssd", "HP Stream")
    assert "n5030" in res["cpu"]


def test_is_broken_false_positive_screen():
    """Mentioning 'экран' alone should NOT flag as broken."""
    res = LaptopParser.regex_parse("IPS экран 15.6 дюймов, Full HD", "Lenovo Ideapad")
    assert res["is_broken"] is False


def test_is_broken_true_for_spare_parts():
    res = LaptopParser.regex_parse("Ноутбук на запчасти, не включается", "Dell E5540")
    assert res["is_broken"] is True


def test_apple_m3_max():
    res = LaptopParser.regex_parse("Apple M3 Max 48gb ram 1tb ssd", "MacBook Pro 16")
    assert "m3 max" in res["cpu"]
    assert res["ram"] == 48
    assert res["ssd"] == 1024


def test_slitted_and_standalone_ssd():
    # 256gb slitted
    res1 = LaptopParser.regex_parse("8gb ram 256gb ssd", "Lenovo")
    assert res1["ssd"] == 256

    # 1tb standalone
    res2 = LaptopParser.regex_parse("16GB / 1TB", "Asus Vivobook")
    assert res2["ssd"] == 1024

    # 256gb standalone
    res3 = LaptopParser.regex_parse("8gb ram 256gb", "Dell Inspiron")
    assert res3["ssd"] == 256
