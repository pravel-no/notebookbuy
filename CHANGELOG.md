# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-17

### Added

- GraphQL scraper for 999.md laptop listings with price history ([lappars.py](lappars.py))
- Analyzer pipeline: regex parsing, Passmark benchmarks, optional Gemini AI ([laptop_analyzer_v3.py](laptop_analyzer_v3.py))
- Streamlit dashboard with filters, charts, and export ([laptop_dashboard.py](laptop_dashboard.py))
- Dynamic USD/EUR → MDL exchange rates with 24h cache ([currency.py](currency.py))
- SQLite schema with migrations ([db.py](db.py))
- CI workflow (Ruff + pytest on Python 3.10 and 3.12)
- Test suite (35 tests) for parser, scoring, currency, and database

### Fixed

- Import `USD_TO_MDL` / `EUR_TO_MDL` from `currency` instead of `scoring`
- GraphQL: use `description: feature(id: 13)` after 999.md removed the `body` field
- SSD parser: treat explicit `gb` units correctly (e.g. `1 gb ssd` → 1 GB, not 1 TB)

[1.0.0]: https://github.com/pravel-no/notebookbuy/releases/tag/v1.0.0
