import tushare as ts
import json, csv, os

ts.set_token('5786743e32ed0a3472d784b70cb7a2692caf675438701623112a2d2a')
pro = ts.pro_api()

out = r"E:\BA工作坊—量化交易"

# 获取美的集团 A 股日线
print("Fetching Midea A-share...")
df_a = pro.daily(ts_code='000333.SZ', start_date='20250704', end_date='20260704',
    fields=['ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'])
df_a = df_a.sort_values('trade_date', ascending=False)
a_data = df_a.to_dict('records')
print(f"A-share: {len(a_data)} records")

with open(os.path.join(out, "midea_daily.json"), "w", encoding="utf-8") as f:
    json.dump(a_data, f, ensure_ascii=False, indent=2)
with open(os.path.join(out, "midea_daily.csv"), "w", newline="", encoding="utf-8") as f:
    if a_data:
        w = csv.DictWriter(f, fieldnames=a_data[0].keys())
        w.writeheader(); w.writerows(a_data)

# 获取基本信息
print("Fetching stock info...")
df_info = pro.stock_basic(ts_code='000333.SZ', fields=['ts_code','name','area','industry','list_date'])
print(df_info.to_string())
