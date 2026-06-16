"""
==========================================================
INFOTACT INTERNSHIP - PROJECT 1
Multi-Touch Marketing Attribution & ROI Dashboard
----------------------------------------------------------
WEEK 2: Advanced SQL & Attribution Logic
==========================================================
- Load cleaned data into SQLite database
- Write Window Function queries to sequence user journeys
- Build First-Touch, Last-Touch, Linear attribution models
"""

import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# ----------------------------------------------------------
# STEP 1: LOAD CLEANED DATA & CREATE SQLite DATABASE
# ----------------------------------------------------------
print("=" * 60)
print("STEP 1: Loading cleaned data into SQLite")
print("=" * 60)

wa  = pd.read_csv('touchpoints_clean.csv',  parse_dates=['timestamp'])
crm = pd.read_csv('conversions_clean.csv',  parse_dates=['converted_at'])
sp  = pd.read_csv('adspend_clean.csv')

con = sqlite3.connect('attribution.db')

wa.to_sql('touchpoints',  con, if_exists='replace', index=False)
crm.to_sql('conversions', con, if_exists='replace', index=False)
sp.to_sql('ad_spend',     con, if_exists='replace', index=False)
con.commit()

tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"  Tables created: {[t[0] for t in tables]}")
print(f"  touchpoints rows : {con.execute('SELECT COUNT(*) FROM touchpoints').fetchone()[0]:,}")
print(f"  conversions rows : {con.execute('SELECT COUNT(*) FROM conversions').fetchone()[0]:,}")
print(f"  ad_spend rows    : {con.execute('SELECT COUNT(*) FROM ad_spend').fetchone()[0]:,}")

# ----------------------------------------------------------
# STEP 2: USER JOURNEY VIEW — Window Function to sequence
#         each user's touchpoints before their conversion
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2: Building user_journeys view (Window Functions)")
print("=" * 60)

con.execute("DROP VIEW IF EXISTS user_journeys")
con.execute("""
CREATE VIEW user_journeys AS
SELECT
    t.log_id,
    t.user_id,
    t.timestamp          AS touch_time,
    t.channel,
    t.campaign,
    t.touch_seq,
    t.total_touches,
    t.touch_position,
    c.conversion_id,
    c.converted_at,
    c.revenue,
    -- Derived attribution weights
    ROUND(1.0 / t.total_touches, 6)                           AS linear_weight,
    CASE WHEN t.touch_position = 'first' THEN 1.0 ELSE 0.0 END AS first_touch_weight,
    CASE WHEN t.touch_position = 'last'  THEN 1.0 ELSE 0.0 END AS last_touch_weight
FROM touchpoints t
INNER JOIN conversions c
    ON t.user_id = c.user_id
    AND t.timestamp <= c.converted_at
""")
con.commit()

sample = pd.read_sql("""
    SELECT user_id, channel, campaign, touch_seq, total_touches,
           touch_position, revenue, linear_weight,
           first_touch_weight, last_touch_weight
    FROM user_journeys
    LIMIT 8
""", con)
print("  Sample user_journeys view:")
print(sample.to_string(index=False))

# ----------------------------------------------------------
# STEP 3: FIRST-TOUCH ATTRIBUTION
#         100% credit to the very first channel
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: First-Touch Attribution")
print("=" * 60)

first_touch = pd.read_sql("""
    SELECT
        channel,
        SUM(revenue * first_touch_weight)      AS attributed_revenue,
        COUNT(DISTINCT conversion_id)           AS conversions,
        ROUND(SUM(revenue * first_touch_weight)
              / SUM(SUM(revenue * first_touch_weight)) OVER() * 100, 2) AS pct_credit
    FROM user_journeys
    GROUP BY channel
    ORDER BY attributed_revenue DESC
""", con)
print(first_touch.to_string(index=False))

# ----------------------------------------------------------
# STEP 4: LAST-TOUCH ATTRIBUTION
#         100% credit to the final channel before conversion
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 4: Last-Touch Attribution")
print("=" * 60)

last_touch = pd.read_sql("""
    SELECT
        channel,
        SUM(revenue * last_touch_weight)       AS attributed_revenue,
        COUNT(DISTINCT conversion_id)           AS conversions,
        ROUND(SUM(revenue * last_touch_weight)
              / SUM(SUM(revenue * last_touch_weight)) OVER() * 100, 2) AS pct_credit
    FROM user_journeys
    GROUP BY channel
    ORDER BY attributed_revenue DESC
""", con)
print(last_touch.to_string(index=False))

# ----------------------------------------------------------
# STEP 5: LINEAR ATTRIBUTION
#         Credit split equally across all touchpoints
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 5: Linear Attribution")
print("=" * 60)

linear = pd.read_sql("""
    SELECT
        channel,
        ROUND(SUM(revenue * linear_weight), 2) AS attributed_revenue,
        COUNT(DISTINCT conversion_id)           AS conversions,
        ROUND(SUM(revenue * linear_weight)
              / SUM(SUM(revenue * linear_weight)) OVER() * 100, 2) AS pct_credit
    FROM user_journeys
    GROUP BY channel
    ORDER BY attributed_revenue DESC
""", con)
print(linear.to_string(index=False))

# ----------------------------------------------------------
# STEP 6: ATTRIBUTION COMPARISON CHART
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 6: Generating Attribution Comparison Chart")
print("=" * 60)

CH_ORDER = ['Email','Search Ads','Social Media','Display Ads','Referral','Direct Traffic']
COLORS   = ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4']

ft_dict = first_touch.set_index('channel')['pct_credit'].to_dict()
lt_dict = last_touch.set_index('channel')['pct_credit'].to_dict()
ln_dict = linear.set_index('channel')['pct_credit'].to_dict()

channels = [c for c in CH_ORDER if c in ft_dict]
x = np.arange(len(channels)); w = 0.26

fig, axes = plt.subplots(1, 2, figsize=(18, 6))
fig.suptitle('WEEK 2 - Attribution Model Comparison | Infotact Internship',
             fontsize=13, fontweight='bold')

# Chart 1: Side-by-side bars
ax = axes[0]
ax.bar(x-w,   [ft_dict.get(c,0) for c in channels], w, label='First Touch', color='#3B82F6', edgecolor='white')
ax.bar(x,     [ln_dict.get(c,0) for c in channels], w, label='Linear',      color='#10B981', edgecolor='white')
ax.bar(x+w,   [lt_dict.get(c,0) for c in channels], w, label='Last Touch',  color='#F59E0B', edgecolor='white')
ax.set_title('Attribution Credit % by Model & Channel', fontweight='bold')
ax.set_ylabel('% of Total Revenue Attributed')
ax.set_xticks(x); ax.set_xticklabels(channels, rotation=25, ha='right', fontsize=9)
ax.legend(); ax.set_ylim(0, max(max(ft_dict.values()), max(lt_dict.values())) * 1.2)
for i, c in enumerate(channels):
    for offset, d, clr in [(-w, ft_dict, '#3B82F6'), (0, ln_dict, '#10B981'), (w, lt_dict, '#F59E0B')]:
        ax.text(i+offset, d.get(c,0)+0.3, f"{d.get(c,0):.1f}%",
                ha='center', fontsize=7, color='black')

# Chart 2: Stacked horizontal bar showing revenue shift
ax = axes[1]
y = np.arange(len(channels))
models = [('First Touch', ft_dict, '#3B82F6'),
          ('Linear',      ln_dict, '#10B981'),
          ('Last Touch',  lt_dict, '#F59E0B')]
for i, (label, d, color) in enumerate(models):
    vals = [d.get(c, 0) for c in channels]
    ax.barh(y + (i-1)*0.26, vals, 0.26, label=label, color=color, edgecolor='white')
ax.set_yticks(y); ax.set_yticklabels(channels, fontsize=9)
ax.set_xlabel('% Attribution Credit')
ax.set_title('Model Comparison — Revenue Credit Shift\n(Key Insight for CMO)', fontweight='bold')
ax.legend(); ax.axvline(16.7, color='gray', linestyle='--', linewidth=1, label='Equal share (16.7%)')

plt.tight_layout()
plt.savefig('Week2_Attribution_Models.png', dpi=150, bbox_inches='tight')
print("  Saved: Week2_Attribution_Models.png")

# ----------------------------------------------------------
# STEP 7: SAVE ATTRIBUTION TABLES
# ----------------------------------------------------------
first_touch['model'] = 'First Touch'
last_touch['model']  = 'Last Touch'
linear['model']      = 'Linear'
all_models = pd.concat([first_touch, last_touch, linear], ignore_index=True)
all_models.to_csv('attribution_models_output.csv', index=False)
print("  Saved: attribution_models_output.csv")

