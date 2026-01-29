# HORECA Prospecting Engine - Technical Blueprint

Based on the "Smart Intelligence" report provided, we will build a 3-layer data acquisition system.

## 1. The Foundation: Geo-Spatial Scraping (HORECA Capillary)
**Objective**: Map every bar, restaurant, and small hotel in a target zone.
**Tech Stack**: `playwright-stealth` (simulating Apify logic).
**Target Sources**: Google Maps, TheFork.
**Output Fields**: Name, Address, Rating, Review Count, Price Level, Website, Phone (Generic).

## 2. The Decision Makers: Corporate & Hotel Chains
**Objective**: Identify "Who signs the check".
**Target Sources**: AEDH (Asociación Española de Directores de Hotel), LinkedIn (via Google Dorking/Sales Nav simulation).
**Output Fields**: Name, Role (Director de Compras, CEO), LinkedIn URL.

## 3. The Money: Real Estate & Investment (SOCIMIs)
**Objective**: Identify owners of assets (BME Growth).
**Target Sources**: BME Growth "Hechos Relevantes" RSS/Scraper.
**Output**: Investment Alerts (e.g., "All Iron RE buys building in Sevilla").

## Implementation Steps

### [NEW] `departments/sales/lead_scrapers/`
- `maps_scraper.py`: Playwright script to extract businesses from Google Maps coordinates.
- `aedh_hunter.py`: Scraper for association member lists.
- `boe_watcher.py`: A specialized agent that checks official gazettes/SOCIMI reports.

### [NEW] `CRM Enrichment Agent`
- A logic layer that merges Layer 1 (Business) with Layer 2 (Person), respecting RGPD (Corporate emails only unless legitimate interest established).
