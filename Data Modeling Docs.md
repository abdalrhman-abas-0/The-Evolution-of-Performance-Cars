# Evolution of Performance Cars

## Data Pipeline & Model Documentation

---

## Overview

This project follows a three-phase pipeline. First, Python scripts and notebooks scrape [SupercarWorld](https://www.supercarworld.com), acquire the raw data, perform an initial structural cleaning pass, and consolidate everything into two CSV files (`super_cars_data.csv` and `brands.csv`). Second, Power Query (M) inside Power BI Desktop applies a second, deeper cleaning pass on those CSVs — handling type conversions, unit stripping, date parsing, and categorical normalisation that go beyond what the Python stage covers. Third, the Power BI data model is built on top of the cleaned data: dimension tables, relationships, and DAX measures are defined, and the final dashboard visuals are assembled for presentation.

---

## Table of Contents

- [1. Data Acquisition Pipeline](#1-data-acquisition-pipeline)
- [2. Data Sources](#2-data-sources)
- [3. Data Cleaning (Power Query — M)](#3-data-cleaning-power-query--m)
- [4. Data Model & Transformations](#4-data-model--transformations)
- [5. Relationships](#5-relationships)
- [6. Measures](#6-measures)
- [7. Applied Filters](#7-applied-filters)

---

## 1. Data Acquisition Pipeline

The raw data powering this dashboard was assembled through a multi-stage Python pipeline before any Power BI work began. The pipeline runs across two notebooks and one standalone script, producing the two CSV files (`super_cars_data.csv` and `brands.csv`) that the Power BI model consumes.

### 1.1 Stage 1 — Cars Scraping (`scraping_performance_cars.ipynb`)

The primary notebook scrapes [SupercarWorld](https://www.supercarworld.com) for specifications on over 1,100 production supercars. It outputs **8 relational CSV files**, each scoped to a logical data domain to avoid hyper-wide tables, plus an initial `brands.csv`:

| Output File | Contents |
|-------------|----------|
| `cars_basic_info.csv` | Car ID, Name, Production Years, New Price, Used Price, Image URL |
| `cars_rating.csv` | Subjective review scores out of 10 — Costs, Desire, Eco, Features, Handling, Looks, Performance, Practicality, Quality, Sound |
| `cars_overall_rating.csv` | Overall Rating, Money No Object Rating, Bargain Rating |
| `cars_general.csv` | Car layout, drivetrain configuration, country of design |
| `cars_engine.csv` | Engine type, capacity, aspiration, power output, torque |
| `cars_performance.csv` | Top speed, 0–60 mph, 0–100 mph, power-to-weight ratios |
| `cars_dimensions.csv` | Total weight, length, width, height, wheelbase |
| `brands.csv` *(v1)* | Brand ID, Brand Name, Logo URL (low-res), Flag URL, Country of Origin |

**Key parsing functions:**

- `get_page(url)` — performs an HTTP GET and returns a `selectolax` DOM tree for fast CSS-selector querying.
- `get_brands(web_page, domain)` — parses the brand catalog to capture brand-listing anchors.
- `car_crawler(car_link)` — fetches each car's page and uses regex to resolve its unique `car_id`.
- `extract_car_info(car_id, web_page, domain)` — orchestrates HTML table extraction via `pd.read_html` / `io.StringIO` and dispatches subsets to helper parsers (`get_car_details`, `get_car_ratting`, `get_basic_info`).

**Politeness controls:** a 1.5-second delay is applied between every page request. If a download fails, the script waits 62 seconds before one retry attempt; two consecutive failures terminate the run to allow debugging.

### 1.2 Stage 2 — High-Resolution Brand Logos (`scraping_brands.py`)

A standalone script re-crawls the brand catalog specifically to retrieve higher-quality logo assets not captured by the main scraper. It operates through a 4-stage pipeline:

```
[Target Domain] → [Extract Brand Names] → [Map Logo Anchors] → [Resolve Country Flags] → [Export CSV]
```

- **DOM Parsing**: The master index is loaded into a `selectolax.parser.HTMLParser` and queried via the CSS selector `tr > td[height="50"] > a[name]`.
- **Multi-Attribute Mapping**: Brand IDs are generated on an incrementing counter; Logo CDN paths are constructed by URL-encoding the brand name (spaces → `%20`).
- **Country Resolution**: For each brand, the script visits its first listed vehicle page and isolates the country flag graphic (`table > tbody > tr > td:nth-child(3) > a > img`) to derive the country name from the image filename.

Output: `brands_2.csv` — containing Brand ID, Brand, Logo (high-res), Flag, Country.

### 1.3 Stage 3 — Brands Table Consolidation (manual)

The two brand tables are merged to produce the final `brands.csv`:

1. `brands_2.csv` (high-res logos) and the `brands.csv` produced by the scraper notebook are joined on Brand ID.
2. The `Logo` column from `brands_2.csv` is used as the primary source for logo URLs; any empty cells are back-filled from the matching `Logo` value in the original `brands.csv`, ensuring complete logo coverage across all brands.
3. The `foundation` column (brand founding year) is populated using an AI search feature to fill gaps not available on the scraped source.
4. The consolidated file is saved as `brands.csv` and `brands_2.csv` is deleted.

Final `brands.csv` schema:

| Column | Type | Description |
|--------|------|-------------|
| `Brand ID` | `int64` | Incremental primary key for relational joins |
| `Brand` | `string` | Full commercial manufacturer name |
| `Logo` | `string` | Absolute URL to the brand logo image (high-res where available) |
| `Flag` | `string` | Absolute URL to the country flag image |
| `Country` | `string` | Manufacturer's country of origin |
| `foundation` | `int64` | Brand founding year |

### 1.4 Stage 4 — Data Cleaning & Consolidation (`Data_cleaning.ipynb`)

The cleaning notebook performs two roles: it restructures the brands-to-cars linkage and merges all car CSV files into a single flat file.

**Brand ID injection:** The brand name is extracted from `cars_basic_info.csv` for each car and matched against `brands.csv` to add a `Brand ID` foreign key column, establishing the relational link between cars and brands before any Power BI work.

**CSV consolidation:** All 7 car-domain CSV files (`cars_basic_info`, `cars_rating`, `cars_overall_rating`, `cars_general`, `cars_engine`, `cars_performance`, `cars_dimensions`) are merged on Car ID into a single `super_cars_data.csv`. All individual domain CSV files are then deleted, leaving only `super_cars_data.csv` and `brands.csv` as the two clean source files loaded into Power BI.

**Cleaning operations applied in Python:**

- Ghost columns and unnamed artefact columns generated by irregular HTML table structures during scraping are dropped.
- Rows representing concept cars (no Overall Rating or missing key technical metrics) are filtered out.
- Currency characters (`£`), unit markers (`mph`, `bhp`, `lbs`, etc.), rating denominators (`/10`), and percentage symbols (`%`) are stripped and columns are recast to `int64` / `float64`.
- Price range strings (e.g. `"£100,000 - £150,000"`) and placeholder strings (e.g. `"£n/a"`) are handled and nulled.

---

## 2. Data Sources

The model is built from two source files:

| File | Contents |
|------|----------|
| `super_cars_data.csv` | Primary source — 57 columns covering car identity, production dates, pricing, dimensions, engine specifications, performance figures, and subjective rating scores. Loaded into all tables except Dim Brands. |
| `brands.csv` | Secondary source — loaded exclusively into Dim Brands. Contains Brand ID, Brand name, Logo URL, Foundation year, Country of origin, and a Flag image URL. |

---

## 3. Data Cleaning (Power Query — M)

All cleaning steps below are applied within the fact table query (`_ Fact_Cars`) on the primary CSV source. The steps are documented in the order they are executed in the M query.

### 3.1 Null & Empty-String Handling

Empty strings are globally replaced with null across all columns before any type conversions are applied. Following that replacement, six categorical columns are filled forward with the literal string `"N/A"` to ensure they remain filterable in visuals rather than producing blank slicer entries:

- Class, Body, Layout, Transmission, Type (later renamed Engine Tech), and Details (later renamed Engine Type)

This two-pass approach — null first, then "N/A" selectively — preserves nulls on numeric and free-text columns while guaranteeing no blank categories appear in dimension slicers.

### 3.2 Price Cleaning

New Price is stored as a formatted sterling string in the source. The following transformations are applied in sequence:

- The literal string `"£n/a"` is replaced with `"null"` (text), then the £ prefix is stripped from all remaining values, and the column is cast to Int64.
- Used Price rows containing `"£n/a - £n/a"` are set to null. The entire column is subsequently dropped from the fact table.

### 3.3 Unit-Suffix Stripping

Numeric columns arrive from the CSV as strings with embedded unit labels. Each suffix is removed via text replacement before the column is cast to its target numeric type:

| Column | Suffix Removed |
|--------|---------------|
| Weight lbs | ` lbs` |
| Engine Capacity in3 | ` in3` |
| Max Power bhp | ` bhp` |
| Max Power rpm | `rpm` |
| Max Torque lb/ft | `lb/ft` |
| Max Torque rpm | `rpm` |
| Power to Weight bhp/ton | `bhp/ton` |
| Torque to Weight | `lbft/ton` |
| Top Speed mph | `mph` |
| 0 - 60 mph sec | `sec` |

After suffix removal, empty strings left by cells that previously contained only the unit token are replaced with null before type casting.

### 3.4 Production Date Parsing

The raw Production column contains year-range strings (e.g. `"1990 - 2005"`) with open-ended entries for still-in-production cars written as `"1990 - date"`. Parsing proceeds through the following steps:

- The column is split on `" - "` into three parts: Production.1 (start year), Production.2 (end year or "date"), and Production.3 (artefact column — immediately dropped).
- The string `"date"` in Production.2 is replaced with an empty string, which — after casting to Int64 — yields null for open-ended rows.
- A helper column `"01/01/"` is added and duplicated. Each copy is merged by concatenation with its respective year integer column, producing full date strings (e.g. `"01/01/1990"`) for both start and end dates.
- For open-ended cars, the null end year had been temporarily replaced with 0 before merging, producing the sentinel string `"01/01/0"`. This sentinel is then replaced with null before both columns are cast to date type.
- Production End is subsequently **dropped** from the fact table — only Production Start is retained and used in the data model.

### 3.5 Rating Score Extraction

Subjective rating columns (Performance, Handling, Looks, Features, Quality, Costs, Desire, Eco, Practicality, Sound) are stored in the source as `"X/10"` strings. The value to the left of the `"/"` delimiter is extracted via `Text.BeforeDelimiter` and the resulting columns are cast to integer. Overall Rating, Money No Object, and Bargain Rating arrive as percentages and are loaded directly without this extraction step.

### 3.6 Max Power & Max Torque Splitting

Both columns are stored in the source as composite `"value @ rpm"` strings. Each is split on the `"@"` delimiter into two separate columns:

- Max Power → Max Power bhp and Max Power rpm
- Max Torque → Max Torque lb/ft and Max Torque rpm

Unit suffixes are then stripped from the value columns as described in section 3.3, and the rpm columns have `"rpm"` removed before being cast to Int64. Empty strings resulting from cells that held no rpm value are replaced with null.

### 3.7 Columns Dropped

The following columns are removed from the fact table as they are not used in any dashboard visual or measure:

| Category | Columns Removed |
|----------|----------------|
| Pricing | Used Price (dropped after null-fill; New Price £ also dropped after cleaning — price data is not exposed in the current model) |
| Dimensions | Length, Width, Height, Number Built, Wheels (F/R), Tyres (F/R), Fuel Capacity |
| Engine detail | Specific Output, Compression, Bore x Stroke, Fuel Consumption, Emissions |
| Performance intervals | 0-30 mph, 0-100 mph, 0-124 mph, 0-186 mph, 30-70 mph, Standing Quarter Mile, 60-0 mph, 0-100-0 mph, Ring Lap Time, Lateral Accn, Drag Cd |
| Production | Production End (retained only during date parsing; dropped before model load) |

---

## 4. Data Model & Transformations

### 4.1 Star Schema

The model follows a star schema pattern. The central fact table (`_ Fact_Cars`) holds one row per car, retaining all numeric performance columns plus surrogate foreign keys that replace the original categorical text columns. Dimension tables surround the fact table and are joined via those integer keys.

Normalisation is applied to six categorical dimensions. For each, the original text column in the fact table is replaced with an integer surrogate ID via a LEFT JOIN to the corresponding dimension table:

| Dimension Table | Fact Column Replaced |
|-----------------|---------------------|
| Dim Class | Class → Class ID |
| Dim Body | Body → Body ID |
| Dim Layout | Layout → Layout ID |
| Dim Engine Tech | Engine Tech → Engine Tech ID |
| Dim Engine Type | Engine Type → Engine Type ID |
| Transmissions_raw | Transmission → Transmission Config ID |

### 4.2 Dimension Table Generation

Each standard dimension table (Dim Class, Dim Body, Dim Layout, Dim Engine Tech, Dim Engine Type) is generated from the same primary CSV using an identical pattern:

- **Select** the single relevant column from the source.
- **Deduplicate** via `Table.Distinct`.
- **Add** an auto-incrementing integer index starting at 1 as the surrogate key.
- **Reorder** columns so the key leads (e.g. Class ID, Class).

### 4.3 Transmission Many-to-Many Resolution

Because a single car can have multiple transmission types recorded as a comma-separated string, a bridge table pattern is used to resolve the many-to-many relationship. Four tables collaborate:

| Table | Role |
|-------|------|
| Transmissions_raw | Stores each unique raw transmission config string with a surrogate Transmission Config ID. Joined to `_ Fact_Cars` on the config string to inject the Config ID into the fact table. |
| Transmissions_type | Intermediate helper — holds the secondary split values from composite config strings (e.g. the second type in `"6-Speed Manual, Automatic"`). Appended into the bridge during construction. |
| Dim Transmissions | Holds deduplicated individual transmission type labels (e.g. `"6-Speed Manual"`, `"Automatic"`) with a unique Transmission ID. |
| Transmissions_bridge | Junction table — maps each Transmission Config ID (from Transmissions_raw) to one or more Transmission ID values (from Dim Transmissions). This is the table through which `_ Fact_Cars` relates to Dim Transmissions via a many-to-many relationship on Transmission Config ID. |

### 4.4 Power to Weight — RAW Column vs. DAX Calculated Column

The source column Power to Weight is renamed in Power Query to `Power to Weight bhp/ton RAW` after unit-suffix stripping. The clean, authoritative version used in the model is a DAX calculated column defined directly on the fact table, which ensures consistent calculation across all rows regardless of source data quality.

### 4.5 Date Table

The Date table is a DAX calculated table generated from the Production Start column of `_ Fact_Cars`. It serves as the standard time-intelligence axis and is related to the fact table via a single active relationship on Production Start date.

### 4.6 Dim Brands

Dim Brands is loaded from the separate `brands.csv` file (not the primary source CSV). It is imported with a fixed schema of six columns:

- Brand ID (Int64 — primary key)
- Brand — brand name text
- Logo — URL to the brand logo image
- foundation — brand founding year
- country — country of origin
- Flag — URL to the country flag image

It joins to `_ Fact_Cars` on Brand ID.

---

## 5. Relationships

The model contains 10 active relationships. All are Many-to-One (from fact to dimension) with one-directional cross-filtering, with the exception of the bridge table relationship which is Many-to-Many with bidirectional filtering.

| From Table | From Column | To Table | To Column | Cardinality | Cross-Filter |
|------------|-------------|----------|-----------|-------------|--------------|
| `_ Fact_Cars` | Engine Tech ID | Dim Engine Tech | Engine Tech ID | Many → One | One Direction |
| `_ Fact_Cars` | Engine Type ID | Dim Engine Type | Engine Type ID | Many → One | One Direction |
| `_ Fact_Cars` | Class ID | Dim Class | Class ID | Many → One | One Direction |
| `_ Fact_Cars` | Layout ID | Dim Layout | Layout ID | Many → One | One Direction |
| `_ Fact_Cars` | Body ID | Dim Body | Body ID | Many → One | One Direction |
| `_ Fact_Cars` | Brand ID | Dim Brands | Brand ID | Many → One | One Direction |
| `_ Fact_Cars` | Production Start | Date | Date | Many → One | One Direction |
| `Transmissions_bridge` | Transmission Config ID | `_ Fact_Cars` | Transmission Config ID | Many → Many | Both Directions |
| `Transmissions_bridge` | Transmission ID | Dim Transmissions | Transmission ID | Many → One | One Direction |
| Date | Date | LocalDateTable | Date | Many → One | One Direction |

---

## 6. Measures

All measures are defined in a dedicated `_Measures` table. The measure set uses `MEDIAN` for continuous numeric fields and `COUNT` for volume. Two measures serve as label strings for card visuals.

> **Note:** The measure `MED Power to Wieght` and the label `New Production Lable` contain typos from the source model ("Wieght" and "Lable") — these names are preserved here as-is to reflect the live model.

| Measure | DAX Expression | Format String |
|---------|---------------|---------------|
| Total New Production | `COUNT('_ Fact_Cars'[Production Start])` | `0` |
| Total Production Card | `"New Production: "&[Total New Production]` | — |
| New Production Lable | `"Releases"` | — |
| MED bhp | `MEDIAN('_ Fact_Cars'[Max Power bhp])` | `0` |
| MED Torque | `MEDIAN('_ Fact_Cars'[Max Torque lb/ft])` | — |
| MED Topspeed | `MEDIAN('_ Fact_Cars'[Top Speed mph])` | `0` |
| MED Engine Capacity | `MEDIAN('_ Fact_Cars'[Engine Capacity in3])` | — |
| MED Money | `MEDIAN('_ Fact_Cars'[Money No Object])*10` | — |
| MED Bargain | `MEDIAN('_ Fact_Cars'[Bargain Rating])*10` | — |
| MED Overall Rating | `MEDIAN('_ Fact_Cars'[Overall Rating])*10` | — |
| MED Desire | `MEDIAN('_ Fact_Cars'[Desire])` | — |
| MED Looks | `MEDIAN('_ Fact_Cars'[Looks])` | — |
| MED Sound | `MEDIAN('_ Fact_Cars'[Sound])` | — |
| MED 0-60 | `MEDIAN('_ Fact_Cars'[0 - 60 mph sec])` | — |
| MED Quality | `MEDIAN('_ Fact_Cars'[Quality])` | — |
| MED Power to Wieght | `MEDIAN('_ Fact_Cars'[Power to Weight bhp/ton])` | — |

---

## 7. Applied Filters

Two global filters are applied consistently across all analysis in this report. These are not Power Query filters baked into the tables — they are slicer/filter-level exclusions applied at the report layer and must be respected in any DAX queries run against the model:

| Filter | Rationale |
|--------|-----------|
| Exclude Class = "Concept" | Concept cars are not production vehicles. Even where a concept was eventually produced, the production variant typically undergoes such substantial changes from the show car that treating them as equivalent production data would distort the analysis. |
| Exclude Production Start year > 2025 | Vehicles with a production start year of 2026 or later are excluded. The current calendar year is not yet complete, meaning the 2026 cohort is a partial sample and would artificially suppress volume and performance metrics for that year relative to prior full-year cohorts. |