"""
==========================================================
INFOTACT INTERNSHIP - PROJECT 1
Multi-Touch Marketing Attribution & ROI Dashboard
----------------------------------------------------------
WEEK 3: Metric Calculation & Star Schema Data Modeling
==========================================================
- Calculate: Total Spend, CPC, CAC, ROAS per channel
- Build Star Schema: fact_attribution + 3 dimension tables
- Export final Excel model for Power BI / Tableau
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

con = sqlite3.connect('attribution.db')

# ----------------------------------------------------------
# STEP 1: CALCULATE CORE KPIs
# ----------------------------------------------------------
print("=" * 60)
print("STEP 1: Calculating Core KPIs")
print("=" * 60)

# --- Total Spend, Impressions, Clicks, CPC from ad_spend ---
spend_kpi = pd.read_sql("""
    SELECT
        channel,
        total_spend,
        impressions,
        clicks,
        ROUND(total_spend / clicks, 4)       AS cpc,
        ROUND(clicks * 100.0 / impressions, 4) AS ctr_pct
    FROM ad_spend
    ORDER BY total_spend DESC
""", con)

# --- Conversions & Revenue from CRM ---
crm_kpi = pd.read_sql("""
    SELECT COUNT(*) AS total_conversions,
           ROUND(SUM(revenue), 2)  AS total_revenue,
           ROUND(AVG(revenue), 2)  AS avg_order_value
    FROM conversions
""", con)

# --- Linear attribution revenue per channel (fairest model) ---
linear_rev = pd.read_sql("""
    SELECT
        channel,
        ROUND(SUM(revenue * linear_weight), 2)  AS linear_attributed_revenue,
        COUNT(DISTINCT conversion_id)            AS attributed_conversions
    FROM user_journeys
    GROUP BY channel
""", con)

# --- Merge all KPIs ---
kpi_master = spend_kpi.merge(linear_rev, on='channel', how='left')
kpi_master['roas']       = (kpi_master['linear_attributed_revenue'] / kpi_master['total_spend']).round(3)
kpi_master['cac']        = (kpi_master['total_spend'] / kpi_master['attributed_conversions'].replace(0, np.nan)).round(2)
kpi_master['conv_rate']  = (kpi_master['attributed_conversions'] / kpi_master['clicks'] * 100).round(3)

print("\n  KPI MASTER TABLE:")
print(kpi_master[[
    'channel','total_spend','cpc','linear_attributed_revenue',
    'roas','cac','attributed_conversions','conv_rate'
]].to_string(index=False))

print(f"\n  Overall:")
print(f"  Total Ad Spend  : ${kpi_master['total_spend'].sum():>12,.2f}")
print(f"  Total Revenue   : ${crm_kpi['total_revenue'].iloc[0]:>12,.2f}")
print(f"  Total Conv.     : {crm_kpi['total_conversions'].iloc[0]:>13,}")
print(f"  Avg Order Value : ${crm_kpi['avg_order_value'].iloc[0]:>12,.2f}")
print(f"  Overall ROAS    : {(crm_kpi['total_revenue'].iloc[0]/kpi_master['total_spend'].sum()):>13.3f}x")

# ----------------------------------------------------------
# STEP 2: STAR SCHEMA — Fact & Dimension Tables
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Building Star Schema")
print("=" * 60)

# DIM 1: dim_channel
dim_channel = pd.DataFrame({
    'channel_key': range(1, 7),
    'channel': ['Email','Search Ads','Social Media','Display Ads','Referral','Direct Traffic'],
    'channel_type': ['Owned','Paid','Paid','Paid','Earned','Organic'],
    'channel_group': ['CRM','Performance','Awareness','Awareness','Referral','Organic'],
})
dim_channel.to_sql('dim_channel', con, if_exists='replace', index=False)
print("  dim_channel  :", dim_channel.shape)

# DIM 2: dim_campaign
wa_df = pd.read_sql("SELECT DISTINCT channel, campaign FROM touchpoints", con)
dim_campaign = wa_df.drop_duplicates().reset_index(drop=True)
dim_campaign.insert(0, 'campaign_key', range(1, len(dim_campaign)+1))
dim_campaign['funnel_stage'] = dim_campaign['campaign'].map({
    'Brand Awareness':    'Awareness',
    'New Product Launch': 'Awareness',
    'Winter Sale':        'Consideration',
    'Discount Offer':     'Conversion',
    'Retargeting':        'Conversion',
    'Organic_Direct':     'Organic',
}).fillna('Unknown')
dim_campaign.to_sql('dim_campaign', con, if_exists='replace', index=False)
print("  dim_campaign :", dim_campaign.shape)

# DIM 3: dim_date
wa_dates = pd.read_sql("SELECT DISTINCT DATE(timestamp) AS date_value FROM touchpoints", con)
wa_dates['date_value'] = pd.to_datetime(wa_dates['date_value'])
dim_date = wa_dates.copy()
dim_date.insert(0, 'date_key', range(1, len(dim_date)+1))
dim_date['day_of_week'] = dim_date['date_value'].dt.day_name()
dim_date['week_number'] = dim_date['date_value'].dt.isocalendar().week.astype(int)
dim_date['month']       = dim_date['date_value'].dt.month_name()
dim_date['is_weekend']  = dim_date['date_value'].dt.weekday >= 5
dim_date.to_sql('dim_date', con, if_exists='replace', index=False)
print("  dim_date     :", dim_date.shape)

# FACT TABLE: fact_attribution
con.execute("DROP TABLE IF EXISTS fact_attribution")
con.execute("""
CREATE TABLE fact_attribution AS
SELECT
    uj.log_id,
    uj.user_id,
    uj.channel,
    uj.campaign,
    DATE(uj.touch_time)         AS date_value,
    uj.touch_seq,
    uj.total_touches,
    uj.touch_position,
    uj.conversion_id,
    uj.revenue,
    ROUND(uj.revenue * uj.linear_weight,      2) AS linear_revenue,
    ROUND(uj.revenue * uj.first_touch_weight, 2) AS first_touch_revenue,
    ROUND(uj.revenue * uj.last_touch_weight,  2) AS last_touch_revenue
FROM user_journeys uj
""")
con.commit()

fact_count = con.execute("SELECT COUNT(*) FROM fact_attribution").fetchone()[0]
print(f"  fact_attribution: {fact_count:,} rows")

print("\n  Star Schema structure:")
print("  fact_attribution")
print("    |--- dim_channel  (JOIN ON channel)")
print("    |--- dim_campaign (JOIN ON channel + campaign)")
print("    |--- dim_date     (JOIN ON date_value)")

# ----------------------------------------------------------
# STEP 3: KPI VISUALISATION CHARTS
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: Generating KPI Charts")
print("=" * 60)

COLORS  = ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4']
palette = dict(zip(kpi_master['channel'], COLORS))

fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('WEEK 3 - KPI Dashboard | Infotact Internship',
             fontsize=14, fontweight='bold')

# Chart 1: ROAS by Channel
ax = axes[0, 0]
roas_sorted = kpi_master.sort_values('roas', ascending=False)
colors_roas = ['#10B981' if r >= 2 else '#F59E0B' if r >= 1 else '#EF4444'
               for r in roas_sorted['roas']]
bars = ax.bar(roas_sorted['channel'], roas_sorted['roas'],
              color=colors_roas, edgecolor='white')
ax.axhline(1.0, color='red',   linestyle='--', linewidth=1.5, label='Break-even (1x)')
ax.axhline(2.0, color='green', linestyle='--', linewidth=1.5, label='Target (2x)')
ax.set_title('ROAS by Channel (Linear Attribution)', fontweight='bold')
ax.set_ylabel('ROAS'); ax.tick_params(axis='x', rotation=25); ax.legend(fontsize=9)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.02,
            f"{b.get_height():.2f}x", ha='center', fontsize=9, fontweight='bold')

# Chart 2: CAC by Channel
ax = axes[0, 1]
cac_sorted = kpi_master.dropna(subset=['cac']).sort_values('cac')
bars = ax.bar(cac_sorted['channel'], cac_sorted['cac'],
              color=[palette.get(c,'#999') for c in cac_sorted['channel']],
              edgecolor='white')
ax.set_title('Customer Acquisition Cost (CAC) by Channel', fontweight='bold')
ax.set_ylabel('CAC ($)'); ax.tick_params(axis='x', rotation=25)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+0.2,
            f"${b.get_height():.2f}", ha='center', fontsize=9, fontweight='bold')

# Chart 3: ROI Scatter — Spend vs Revenue (bubble = conversions)
ax = axes[1, 0]
sc = ax.scatter(
    kpi_master['total_spend'],
    kpi_master['linear_attributed_revenue'],
    s=kpi_master['attributed_conversions'] * 5,
    c=[palette.get(c,'#999') for c in kpi_master['channel']],
    alpha=0.85, edgecolors='white', linewidth=1
)
# Break-even line
max_v = max(kpi_master['total_spend'].max(), kpi_master['linear_attributed_revenue'].max())
ax.plot([0, max_v], [0, max_v], 'r--', linewidth=1.5, label='Break-even (ROAS=1)')
ax.plot([0, max_v], [0, max_v*2], 'g--', linewidth=1.2, alpha=0.6, label='2x ROAS')
for _, row in kpi_master.dropna(subset=['linear_attributed_revenue']).iterrows():
    ax.annotate(row['channel'], (row['total_spend'], row['linear_attributed_revenue']),
                fontsize=8, xytext=(5,5), textcoords='offset points')
ax.set_title('ROI Scatter — Spend vs Revenue\n(Bubble size = Conversions)', fontweight='bold')
ax.set_xlabel('Total Ad Spend ($)'); ax.set_ylabel('Attributed Revenue ($)')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:,.0f}'))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:,.0f}'))
ax.legend(fontsize=8)

# Chart 4: CPC by Channel
ax = axes[1, 1]
cpc_sorted = kpi_master.sort_values('cpc')
bars = ax.barh(cpc_sorted['channel'], cpc_sorted['cpc'],
               color=[palette.get(c,'#999') for c in cpc_sorted['channel']],
               edgecolor='white')
ax.set_title('Cost Per Click (CPC) by Channel', fontweight='bold')
ax.set_xlabel('CPC ($)')
for b in bars:
    ax.text(b.get_width()+0.001, b.get_y()+b.get_height()/2,
            f"${b.get_width():.3f}", va='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('Week3_KPI_Charts.png', dpi=150, bbox_inches='tight')
print("  Saved: Week3_KPI_Charts.png")

# ----------------------------------------------------------
# STEP 4: EXPORT STAR SCHEMA TO EXCEL (for Tableau/Power BI)
# ----------------------------------------------------------
fact = pd.read_sql("SELECT * FROM fact_attribution", con)

with pd.ExcelWriter('StarSchema_PowerBI_Export.xlsx', engine='openpyxl') as writer:
    fact.to_excel(writer,        sheet_name='fact_attribution', index=False)
    dim_channel.to_excel(writer, sheet_name='dim_channel',      index=False)
    dim_campaign.to_excel(writer,sheet_name='dim_campaign',     index=False)
    dim_date.to_excel(writer,    sheet_name='dim_date',         index=False)
    kpi_master.to_excel(writer,  sheet_name='kpi_master',       index=False)

print("  Saved: StarSchema_PowerBI_Export.xlsx")
print(f"         - fact_attribution : {fact.shape[0]:,} rows")
print(f"         - dim_channel      : {dim_channel.shape[0]} rows")
print(f"         - dim_campaign     : {dim_campaign.shape[0]} rows")
print(f"         - dim_date         : {dim_date.shape[0]} rows")
print(f"         - kpi_master       : {kpi_master.shape[0]} rows")
print("\n  WEEK 3 COMPLETE - Commit StarSchema_PowerBI_Export.xlsx to GitHub.")
