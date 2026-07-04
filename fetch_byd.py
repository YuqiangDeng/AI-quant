import tushare as ts, json, csv, os, sys

ts.set_token('5786743e32ed0a3472d784b70cb7a2692caf675438701623112a2d2a')
pro = ts.pro_api()

out = r"E:\BA工作坊—量化交易"

# Fetch BYD data
df = pro.daily(ts_code='002594.SZ', start_date='20250704', end_date='20260704',
    fields=['ts_code','trade_date','open','high','low','close','pre_close','change','pct_chg','vol','amount'])
df = df.sort_values('trade_date', ascending=False).reset_index(drop=True)

data = df.to_dict('records')
print(f"BYD records: {len(data)}")

# Save CSV
csv_path = os.path.join(out, "byd_daily.csv")
with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=data[0].keys())
    w.writeheader(); w.writerows(data)
print(f"CSV saved: {csv_path}")

# Save JSON
json_path = os.path.join(out, "byd_daily.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"JSON saved: {json_path}")

# Generate HTML from SMIC dashboard template
rows = []
for d in data:
    rows.append(f'["{d["trade_date"]}",{d["open"]},{d["high"]},{d["low"]},{d["close"]},{d["vol"]},{d["amount"]}]')
js_array = ",\n  ".join(rows)

with open(os.path.join(out, "smic_dashboard.html"), "r", encoding="utf-8") as f:
    template = f.read()

new_data = f'// 比亚迪 002594.SZ 日线数据 (来源: Tushare Pro)\nconst allData = [\n  {js_array}\n]'

start = template.find('const allData')
end = template.find('];', start) + 2
template = template[:start] + new_data + template[end:]

template = template.replace('中芯国际 (688981.SH) 日线行情', '比亚迪 (002594.SZ) 日线行情')
template = template.replace('中芯国际 688981.SH', '比亚迪 002594.SZ')
template = template.replace('688981.SH', '002594.SZ')
template = template.replace('2025-07-03 ~ 2026-07-02', '2025-07-04 ~ 2026-07-03')

html_path = os.path.join(out, "byd_dashboard.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(template)
print(f"HTML saved: {html_path}")

# Get stock info
try:
    info = pro.stock_basic(ts_code='002594.SZ', fields=['ts_code','name','area','industry','list_date'])
    print(info.to_string(index=False))
except:
    pass
