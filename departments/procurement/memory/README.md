# Adquify Procurement Memory System

This directory acts as the **Long-Term Memory** for the autonomous agents.
All static rules, supplier configurations, and operational constraints must be documented here.

## Directory Structure
- `supplier_rules/`: JSON/YAML files defining how to interact with each specific supplier.
  - `sklum.json`: Selectors, login URLs, margin rules, shipping thresholds.
  - `kave.json`: API keys (if any), scraping intervals.
- `logs/`: Persistent execution logs for auditing.
- `compliance/`: RGPD rules and Robots.txt agreements.

## Usage
Agents must read this directory BEFORE starting any operation to ensure they are using the latest rules.
