import tushare as ts
import json, csv, os

# 设置 token
ts.set_token('5786743e32ed0a3472d784b70cb7a2692caf675438701623112a2d2a')
pro = ts.pro_api()

out = r"E:\BA工作坊—量化交易"

# 获取美的集团 A 股日线数据
# 000333.SZ 深交所主板
print("Fetching Midea A-share data...")
df_a = pro.daily(ts_code='000333.SZ', start_date='20250704', end_date='20260704', fields=[
    'ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'
])
df_a = df_a.sort_values('trade_date', ascending=False)
print(f"A-share records: {len(df_a)}")

# 保存 A 股数据
a_data = df_a.to_dict('records')
with open(os.path.join(out, "midea_daily.json"), "w", encoding="utf-8") as f:
    json.dump(a_data, f, ensure_ascii=False, indent=2)
with open(os.path.join(out, "midea_daily.csv"), "w", newline="", encoding="utf-8") as f:
    if a_data:
        w = csv.DictWriter(f, fieldnames=a_data[0].keys())
        w.writeheader(); w.writerows(a_data)

# 美的集团没有港股，查询确认
print("Checking if Midea has HK listing...")
try:
    df_hk = pro.hk_daily(ts_code='00300.HK', start_date='20250704', end_date='20260704')
    print(f"HK 00300.HK records: {len(df_hk)}")
except Exception as e:
    print(f"No HK data or error: {e}")

print("Done!")
print(f"A股数据已保存: {len(a_data)} 条")
