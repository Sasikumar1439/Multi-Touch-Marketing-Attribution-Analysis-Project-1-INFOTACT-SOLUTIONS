# Project 1: Multi-Touch Marketing Attribution & ROI Dashboard
**Infotact Internship | Sasikumar | Data Analytics**

---

## Problem Statement
E-commerce companies spend across multiple channels but
traditional Last-Click attribution gives all credit to the
final channel. This project builds a Multi-Touch Attribution
model to fairly distribute conversion credit and calculate
true ROAS and CAC per channel.

---

## Datasets
| File | Description | Rows |
|------|-------------|------|
| multi_touch_attribution_data.csv | Raw touchpoint logs | 10,000 |
| web_analytics_logs_Clean.csv | Cleaned with touch sequence | 10,000 |
| crm_conversions_Clean.csv | CRM conversions with revenue | 2,381 |
| ad_spend_summary_Clean.csv | Channel spend, impressions, clicks | 6 |

---

## Week 1 - Data Ingestion and EDA
- Loaded 3 datasets using Python Pandas
- Standardised timestamps to IST timezone
- Removed duplicate touchpoints
- Assigned touch_seq and touch_position per user
- Generated 6 EDA charts
- Saved 3 cleaned output CSVs

**Key Finding:** Average 4.4 touchpoints per user before converting

---

## Week 2 - SQL and Attribution Logic
- Loaded cleaned data into SQLite database
- Built user_journeys VIEW using Window Function
- ROW_NUMBER() OVER(PARTITION BY user_id ORDER BY timestamp)
- Implemented 3 Attribution Models:
  - First-Touch: 100% credit to first channel
  - Last-Touch: 100% credit to last channel
  - Linear: Equal credit split across all touchpoints

---

## Tech Stack
- Python 3 (Pandas, Matplotlib, Seaborn)
- SQL (SQLite with Window Functions)
- Power BI / Tableau
- GitHub
