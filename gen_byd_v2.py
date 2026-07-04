import json, os

out = r"E:\BA工作坊—量化交易"

with open(os.path.join(out, "byd_daily.json"), "r") as f:
    raw = json.load(f)

data = list(reversed(raw))

rows = []
for d in data:
    rows.append(f'["{d["trade_date"]}",{d["open"]},{d["high"]},{d["low"]},{d["close"]},{d["vol"]},{d["amount"]}]')
js_array = ",\n  ".join(rows)

# Compute KPIs
closes = [d["close"] for d in data]
opens = [d["open"] for d in data]
highs = [d["high"] for d in data]
lows = [d["low"] for d in data]
vols = [d["vol"] for d in data]

kpi = {
    "last_close": closes[-1], "last_pct": round((closes[-1]-opens[-1])/opens[-1]*100, 2),
    "high": max(highs), "low": min(lows),
    "range_pct": round((closes[-1]-closes[0])/closes[0]*100, 2),
    "ma5": round(sum(closes[-5:])/5, 2), "ma20": round(sum(closes[-20:])/20, 2),
    "up_days": sum(1 for i in range(1,len(data)) if closes[i]>closes[i-1]),
    "max_up": round(max(((closes[i]-closes[i-1])/closes[i-1]*100) for i in range(1,len(data))), 2),
    "max_down": round(min(((closes[i]-closes[i-1])/closes[i-1]*100) for i in range(1,len(data))), 2),
}
kpi["direction"] = "up" if kpi["last_pct"] >= 0 else "down"

# RSI14
gains, losses = [], []
for i in range(1, len(closes)):
    chg = closes[i]-closes[i-1]
    gains.append(max(chg,0))
    losses.append(max(-chg,0))
avg_g, avg_l = sum(gains[:14])/14, sum(losses[:14])/14
for i in range(14, len(gains)):
    avg_g = (avg_g*13+gains[i])/14
    avg_l = (avg_l*13+losses[i])/14
rsi14 = 100 - 100/(1+avg_g/avg_l) if avg_l else 100

# Read template
with open(os.path.join(out, "byd_template_part1.html"), "r", encoding="utf-8") as f:
    tpl1 = f.read()

with open(os.path.join(out, "byd_template_part2.html"), "r", encoding="utf-8") as f:
    tpl2 = f.read()

with open(os.path.join(out, "byd_template_part3.html"), "r", encoding="utf-8") as f:
    tpl3 = f.read()

html = tpl1 + js_array + tpl2 + json.dumps(round(rsi14, 2)) + tpl3

# Replace KPI placeholders
replacements = {
    "KPI_LAST_CLOSE": f"{kpi['last_close']:.2f}",
    "KPI_PCT": f"{kpi['last_pct']:+.2f}%",
    "KPI_DIR_CLASS": kpi["direction"],
    "KPI_HIGH": f"{kpi['high']:.2f}",
    "KPI_LOW": f"{kpi['low']:.2f}",
    "KPI_RANGE_PCT": f"{kpi['range_pct']:+.2f}%",
    "KPI_RANGE_CLASS": "up" if kpi["range_pct"] >= 0 else "down",
    "KPI_MA5": f"{kpi['ma5']:.2f}",
    "KPI_MA20": f"{kpi['ma20']:.2f}",
    "KPI_RSI": f"{rsi14:.1f}",
    "KPI_UP_DAYS": str(kpi["up_days"]),
    "KPI_TOTAL_DAYS": str(len(data)-1),
    "KPI_UP_PCT": f"{round(kpi['up_days']/(len(data)-1)*100,1)}",
    "KPI_MAX_UP": f"{kpi['max_up']}",
    "KPI_MAX_DOWN": f"{kpi['max_down']}",
}

for k, v in replacements.items():
    html = html.replace(k, v)

# Technical analysis text
ma_status = "bullish" if kpi["ma5"] > kpi["ma20"] else "bearish"
ma_text = "多头排列 (MA5 > MA20)" if ma_status == "bullish" else "空头排列 (MA5 < MA20)"
ma_icon = "🔴" if ma_status == "bullish" else "🟢"
html = html.replace("MA_STATUS_TEXT", ma_text).replace("MA_STATUS_ICON", ma_icon)

close_vs_ma5 = "高于 MA5" if kpi["last_close"] > kpi["ma5"] else "低于 MA5"
close_vs_ma20 = "高于 MA20" if kpi["last_close"] > kpi["ma20"] else "低于 MA20"
html = html.replace("CLOSE_VS_MA5", close_vs_ma5).replace("CLOSE_VS_MA20", close_vs_ma20)

html_path = os.path.join(out, "byd_dashboard.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print("BYD comprehensive dashboard generated!")
