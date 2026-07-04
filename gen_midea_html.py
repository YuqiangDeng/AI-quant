import json, os

out = r"E:\BA工作坊—量化交易"

# Read A data
with open(os.path.join(out, "midea_daily.json"), "r") as f:
    a_data = json.load(f)

# Generate JS data array
rows = []
for d in a_data:
    rows.append(f'["{d["trade_date"]}",{d["open"]},{d["high"]},{d["low"]},{d["close"]},{d["vol"]},{d["amount"]}]')

js_array = ",\n  ".join(rows)

# Read HTML template
with open(os.path.join(out, "smic_dashboard.html"), "r", encoding="utf-8") as f:
    template = f.read()

# Replace SMIC data with Midea data
# Find the allData array section and replace it
old_data_marker = 'const allData = ['
new_data_marker = f'// 美的集团 000333.SZ 日线数据 (来源: Tushare Pro)\nconst allData = [\n  {js_array}\n]'

template = template.replace(f'中芯国际 (688981.SH) 日线行情', '美的集团 (000333.SZ) 日线行情')
template = template.replace(f'中芯国际 688981.SH', '美的集团 000333.SZ')
template = template.replace(f'数据来源: Tushare Pro &middot; 近1年 &middot; 2025-07-03 ~ 2026-07-02', '数据来源: Tushare Pro &middot; 近1年 &middot; 2025-07-04 ~ 2026-07-03')
template = template.replace(f'688981.SH', '000333.SZ')

# Find and replace the allData array
start = template.find('const allData')
end = template.find('];', start) + 2
template = template[:start] + new_data_marker + template[end:]

with open(os.path.join(out, "midea_dashboard.html"), "w", encoding="utf-8") as f:
    f.write(template)

print("Midea dashboard HTML generated!")
