"""
==========================================================
INFOTACT INTERNSHIP - PROJECT 1
Multi-Touch Marketing Attribution & ROI Dashboard
----------------------------------------------------------
WEEK 1: Data Ingestion & Exploratory Data Analysis (EDA)
==========================================================
Files:
  web_analytics_logs.xls   -> 10,000 touchpoint logs (User + Channel + Campaign + Timestamp)
  crm_conversions.xls      -> 2,381 real CRM conversions (User + Revenue + Timestamp)
  ad_spend_summary.xls     -> 6 channel rows (Spend + Impressions + Clicks)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import warnings
warnings.filterwarnings('ignore')

# ----------------------------------------------------------
# STEP 1: LOAD RAW DATA
# ----------------------------------------------------------
print("=" * 60)
print("STEP 1: Loading raw datasets")
print("=" * 60)

wa  = pd.read_csv('web_analytics_logs.xls')
crm = pd.read_csv('crm_conversions.xls')
sp  = pd.read_csv('ad_spend_summary.xls')

print(f"  web_analytics_logs : {wa.shape[0]:,} rows x {wa.shape[1]} cols")
print(f"  crm_conversions    : {crm.shape[0]:,} rows x {crm.shape[1]} cols")
print(f"  ad_spend_summary   : {sp.shape[0]:,} rows x {sp.shape[1]} cols")

# ----------------------------------------------------------
# STEP 2: CLEAN web_analytics_logs  (Touchpoints)
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2A: Cleaning web_analytics_logs")
print("=" * 60)

wa = wa.rename(columns={
    'log_id':    'log_id',
    'User ID':   'user_id',
    'Timestamp': 'timestamp',
    'Channel':   'channel',
    'Campaign':  'campaign'
})

# Parse & standardise timestamp to IST
wa['timestamp'] = pd.to_datetime(wa['timestamp'])
wa['timestamp'] = wa['timestamp'].dt.tz_localize('Asia/Kolkata', ambiguous='NaT', nonexistent='NaT')

# Handle missing UTM: replace blank or NaN campaign with 'unknown'
wa['campaign'] = wa['campaign'].fillna('unknown').replace('', 'unknown')

# Remove duplicates: same user on same channel at same second
dupes = wa.duplicated(subset=['user_id', 'timestamp', 'channel']).sum()
print(f"  Duplicate rows removed : {dupes}")
wa = wa.drop_duplicates(subset=['user_id', 'timestamp', 'channel'])

# Sort by user + time to reconstruct journey order
wa = wa.sort_values(['user_id', 'timestamp']).reset_index(drop=True)

# Add journey sequencing (equivalent to SQL Window Function)
wa['touch_seq']      = wa.groupby('user_id').cumcount() + 1
wa['total_touches']  = wa.groupby('user_id')['touch_seq'].transform('max')
wa['touch_position'] = wa.apply(
    lambda r: 'first' if r['touch_seq'] == 1
    else ('last' if r['touch_seq'] == r['total_touches'] else 'middle'),
    axis=1
)

print(f"  Clean shape            : {wa.shape}")
print(f"  Unique users           : {wa['user_id'].nunique():,}")
print(f"  Channels               : {wa['channel'].unique().tolist()}")
print(f"  Campaigns              : {wa['campaign'].unique().tolist()}")
print(f"  Date range             : {wa['timestamp'].min()} to {wa['timestamp'].max()}")
print(f"  Avg touches/user       : {wa['total_touches'].mean():.2f}")
print(f"  Missing values         : {wa.isnull().sum().sum()}")

# ----------------------------------------------------------
# STEP 3: CLEAN crm_conversions
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2B: Cleaning crm_conversions")
print("=" * 60)

crm = crm.rename(columns={
    'conversion_id':        'conversion_id',
    'User ID':              'user_id',
    'conversion_timestamp': 'converted_at',
    'revenue':              'revenue',
    'status':               'status'
})

crm['converted_at'] = pd.to_datetime(crm['converted_at'])
crm['converted_at'] = crm['converted_at'].dt.tz_localize('Asia/Kolkata', ambiguous='NaT', nonexistent='NaT')

# Keep only Completed conversions
crm = crm[crm['status'] == 'Completed'].copy()
crm['converted'] = 1

print(f"  Clean shape     : {crm.shape}")
print(f"  Revenue range   : ${crm['revenue'].min():.2f} - ${crm['revenue'].max():.2f}")
print(f"  Total revenue   : ${crm['revenue'].sum():,.2f}")
print(f"  Missing values  : {crm.isnull().sum().sum()}")

# ----------------------------------------------------------
# STEP 4: CLEAN ad_spend_summary
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 2C: Cleaning ad_spend_summary")
print("=" * 60)

sp['cpc']       = (sp['total_spend'] / sp['clicks']).round(4)
sp['ctr']       = (sp['clicks']      / sp['impressions'] * 100).round(4)

print(f"  Clean shape     : {sp.shape}")
print(f"  Total spend     : ${sp['total_spend'].sum():,.2f}")
print(f"  Channels        : {sp['channel'].tolist()}")
print(sp[['channel','total_spend','impressions','clicks','cpc','ctr']].to_string(index=False))

# ----------------------------------------------------------
# STEP 5: EDA VISUALISATIONS (6 charts)
# ----------------------------------------------------------
print("\n" + "=" * 60)
print("STEP 3: Generating EDA charts")
print("=" * 60)

CH_ORDER = ['Email','Search Ads','Social Media','Display Ads','Referral','Direct Traffic']
COLORS   = ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6','#06B6D4']
palette  = {ch: COLORS[i] for i, ch in enumerate(CH_ORDER)}

fig, axes = plt.subplots(2, 3, figsize=(20, 11))
fig.suptitle('WEEK 1 EDA - Multi-Touch Attribution | Infotact Internship',
             fontsize=14, fontweight='bold', y=1.01)

# Chart 1: Touchpoints by Channel
ax = axes[0, 0]
ch_cnt = wa['channel'].value_counts().reindex(CH_ORDER).dropna()
bars = ax.bar(ch_cnt.index, ch_cnt.values,
              color=[palette[c] for c in ch_cnt.index], edgecolor='white', linewidth=0.5)
ax.set_title('Total Touchpoints by Channel', fontweight='bold', fontsize=12)
ax.set_ylabel('Count'); ax.tick_params(axis='x', rotation=25)
for b in bars:
    ax.text(b.get_x()+b.get_width()/2, b.get_height()+10,
            f"{int(b.get_height()):,}", ha='center', fontsize=9, fontweight='bold')

# Chart 2: Campaign distribution
ax = axes[0, 1]
camp_cnt = wa['campaign'].value_counts()
ax.pie(camp_cnt.values, labels=camp_cnt.index, autopct='%1.1f%%',
       colors=COLORS[:len(camp_cnt)], startangle=90,
       textprops={'fontsize': 9})
ax.set_title('Touchpoints by Campaign', fontweight='bold', fontsize=12)

# Chart 3: Journey Depth (how many touches before conversion)
ax = axes[0, 2]
journey = wa.groupby('user_id')['total_touches'].first()
jvc = journey.value_counts().sort_index()
bars = ax.bar(jvc.index.astype(str), jvc.values, color='#8B5CF6', edgecolor='white')
ax.set_title('User Journey Depth\n(Touches per User)', fontweight='bold', fontsize=12)
ax.set_xlabel('Number of Touchpoints')
ax.set_ylabel('Number of Users')
avg_line = journey.mean()
ax.axvline(avg_line - 1, color='red', linestyle='--', linewidth=1.5, label=f'Avg={avg_line:.1f}')
ax.legend(fontsize=9)

# Chart 4: First Touch vs Last Touch channel frequency
ax = axes[1, 0]
fc = wa[wa['touch_position']=='first']['channel'].value_counts()
lc = wa[wa['touch_position']=='last' ]['channel'].value_counts()
x = np.arange(len(CH_ORDER)); w = 0.38
ax.bar(x-w/2, [fc.get(c,0) for c in CH_ORDER], w, label='First Touch',
       color='#3B82F6', edgecolor='white')
ax.bar(x+w/2, [lc.get(c,0) for c in CH_ORDER], w, label='Last Touch',
       color='#F59E0B', edgecolor='white')
ax.set_title('First Touch vs Last Touch\nChannel Frequency', fontweight='bold', fontsize=12)
ax.set_ylabel('Count'); ax.set_xticks(x)
ax.set_xticklabels(CH_ORDER, rotation=25, ha='right', fontsize=8); ax.legend()

# Chart 5: Ad Spend vs Clicks (efficiency view)
ax = axes[1, 1]
sc = ax.scatter(sp['total_spend'], sp['clicks'],
                s=sp['impressions']/2000, alpha=0.8,
                color=[palette.get(c,'#999') for c in sp['channel']], edgecolors='white', linewidth=0.8)
for _, row in sp.iterrows():
    ax.annotate(row['channel'], (row['total_spend'], row['clicks']),
                fontsize=8, ha='left', va='bottom',
                xytext=(4, 4), textcoords='offset points')
ax.set_title('Ad Spend vs Clicks\n(Bubble size = Impressions)', fontweight='bold', fontsize=12)
ax.set_xlabel('Total Spend ($)'); ax.set_ylabel('Clicks')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x:,.0f}'))

# Chart 6: Daily conversion volume (CRM)
ax = axes[1, 2]
crm['date'] = crm['converted_at'].dt.date
daily = crm.groupby('date').agg(conversions=('conversion_id','count'),
                                 revenue=('revenue','sum')).reset_index()
ax2 = ax.twinx()
ax.bar(range(len(daily)), daily['conversions'], color='#3B82F6', alpha=0.6, label='Conversions')
ax2.plot(range(len(daily)), daily['revenue'], color='#EF4444', linewidth=2, label='Revenue ($)')
ax.set_title('Daily Conversions & Revenue\n(CRM Data)', fontweight='bold', fontsize=12)
ax.set_ylabel('Conversions'); ax2.set_ylabel('Revenue ($)')
ax.set_xticks(range(0, len(daily), max(1, len(daily)//5)))
ax.set_xticklabels([str(daily['date'].iloc[i]) for i in range(0, len(daily), max(1, len(daily)//5))],
                   rotation=25, ha='right', fontsize=7)
ax.legend(loc='upper left', fontsize=8); ax2.legend(loc='upper right', fontsize=8)

plt.tight_layout()
plt.savefig('Week1_EDA_Charts.png', dpi=150, bbox_inches='tight')
print("  Saved: Week1_EDA_Charts.png")

# ----------------------------------------------------------
# STEP 6: SAVE CLEANED FILES
# ----------------------------------------------------------
wa.to_csv('touchpoints_clean.csv',  index=False)
crm.to_csv('conversions_clean.csv', index=False)
sp.to_csv('adspend_clean.csv',      index=False)

print("\n  Saved: touchpoints_clean.csv  ", wa.shape)
print("  Saved: conversions_clean.csv  ", crm.shape)
print("  Saved: adspend_clean.csv      ", sp.shape)

