#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
update_turtle_data.py — 海龟法则看板·每日数据增量更新脚本

功能：
  对每只标的，用 akshare 新浪源拉取全量前复权日线，
  仅追加 trade_date > 本地 CSV 末行日期 的新行（幂等去重），写回 data/*.csv。

特点：
  - A 股 / 港股 自动分流（stock_zh_a_daily / stock_hk_daily）
  - UTF-8-SIG 输出，与既有标准字段完全一致
  - 网络/依赖失败时不崩溃，打印告警并以 exit 0 退出（便于 CI 降级继续）
  - 支持 --data-dir 指定数据目录（默认：脚本同级的 data/）

用法：
  python update_turtle_data.py
  python update_turtle_data.py --data-dir /path/to/data
"""

import argparse
import csv
import os
import sys
from datetime import datetime

# ----------------------------------------------------------------------------
# 标的清单（与看板一致）
# ----------------------------------------------------------------------------
SYMBOLS = [
    {"name": "中芯国际A", "ts_code": "688981.SH", "market": "A", "ak": "688981", "file": "smic_daily_qfq.csv"},
    {"name": "比亚迪",    "ts_code": "002594.SZ", "market": "A", "ak": "002594", "file": "byd_daily_qfq.csv"},
    {"name": "长江电力",  "ts_code": "600900.SH", "market": "A", "ak": "600900", "file": "yangtze_power_daily_qfq.csv"},
    {"name": "美的集团",  "ts_code": "000333.SZ", "market": "A", "ak": "000333", "file": "midea_daily_qfq.csv"},
    {"name": "中芯国际H", "ts_code": "00981.HK",  "market": "H", "ak": "00981",  "file": "smic_hk_daily.csv"},
]

FIELDS = ["ts_code", "trade_date", "open", "high", "low", "close",
          "pre_close", "change", "pct_chg", "vol", "amount"]


def last_date(path):
    """返回 CSV 中最大的 trade_date（int YYYYMMDD），无文件则 0。"""
    if not os.path.exists(path):
        return 0
    dmax = 0
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                d = int(row["trade_date"])
                if d > dmax:
                    dmax = d
            except (ValueError, KeyError, TypeError):
                continue
    return dmax


DATE_KEYS = ("date", "day", "datetime", "日期", "时间")
OPEN_KEYS = ("open", "开盘")
HIGH_KEYS = ("high", "最高")
LOW_KEYS = ("low", "最低")
CLOSE_KEYS = ("close", "收盘")
VOL_KEYS = ("volume", "vol", "成交量", "vomume")


def _pick(df, keys):
    """在 df 列中按候选关键字（忽略大小写）挑出实际列名。"""
    low = {str(c).lower(): c for c in df.columns}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return None


def _normalize(df, sym):
    """把任意 akshare 返回的日线 df 规范为 FIELDS 行列表（按日期升序）。"""
    dcol = _pick(df, DATE_KEYS)
    ocol = _pick(df, OPEN_KEYS)
    hcol = _pick(df, HIGH_KEYS)
    lcol = _pick(df, LOW_KEYS)
    ccol = _pick(df, CLOSE_KEYS)
    vcol = _pick(df, VOL_KEYS)
    if not (dcol and ocol and hcol and lcol and ccol):
        return None
    rows = []
    prev = None
    for _, rec in df.iterrows():
        try:
            dt = str(rec[dcol]).replace("-", "").strip()[:8]
            trade_date = int(dt)
            o = float(rec[ocol])
            h = float(rec[hcol])
            l = float(rec[lcol])
            c = float(rec[ccol])
        except (ValueError, TypeError):
            continue
        vol = float(rec[vcol]) if vcol else 0.0
        pre = prev if prev is not None else c
        change = round(c - pre, 4)
        pct = round(change / pre * 100, 4) if pre else 0.0
        # amount（千元）估算：价格 × 成交量(手) × 100 / 1000
        amount = round(c * vol * 100 / 1000, 2) if vol else 0.0
        rows.append({
            "ts_code": sym["ts_code"], "trade_date": trade_date,
            "open": o, "high": h, "low": l, "close": c,
            "pre_close": pre, "change": change, "pct_chg": pct,
            "vol": vol, "amount": amount,
        })
        prev = c
    rows.sort(key=lambda x: x["trade_date"])
    return rows


def fetch_full(sym):
    """多数据源拉取全量前复权日线，返回按 FIELDS 组织的行列表（最新在后）。

    数据源按序尝试，任一成功即用；全部失败则优雅返回 []。
    A 股：先新浪 stock_zh_a_daily，失败再试东财 stock_zh_a_hist。
    港股：新浪 stock_hk_daily。
    """
    try:
        import akshare as ak
    except Exception as e:  # noqa
        print(f"  [跳过] {sym['name']}：无法导入 akshare（{e}）")
        return []

    attempts = []
    if sym["market"] == "H":
        attempts.append(("港股新浪", lambda: ak.stock_hk_daily(symbol=sym["ak"], adjust="qfq")))
    else:
        attempts.append(("A股新浪", lambda: ak.stock_zh_a_daily(symbol=sym["ak"], adjust="qfq")))
        code = sym["ts_code"].split(".")[0]
        attempts.append(("A股东财", lambda: ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")))

    for label, fn in attempts:
        try:
            df = fn()
        except Exception as e:  # noqa
            print(f"    - {label} 失败：{type(e).__name__}")
            continue
        if df is None or len(df) == 0:
            print(f"    - {label} 返回空")
            continue
        rows = _normalize(df, sym)
        if rows:
            print(f"    - {label} 成功（{len(rows)} 行）")
            return rows
        print(f"    - {label} 列无法识别")
    print(f"  [跳过] {sym['name']}：全部数据源失败")
    return []


def append_new(data_dir, sym, rows):
    """把 rows 中 trade_date > 本地末行的部分追加写入 CSV；返回新增行数。"""
    path = os.path.join(data_dir, sym["file"])
    if not os.path.exists(path):
        # 首次：直接写入全量
        return write_all(path, rows)
    dmax = last_date(path)
    new_rows = [r for r in rows if r["trade_date"] > dmax]
    if not new_rows:
        print(f"  [无新增] {sym['name']}（本地已至 {dmax}）")
        return 0
    with open(path, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        for r in new_rows:
            w.writerow(r)
    print(f"  [追加] {sym['name']}：+{len(new_rows)} 行（{new_rows[0]['trade_date']}..{new_rows[-1]['trade_date']}）")
    return len(new_rows)


def write_all(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"  [写入] {os.path.basename(path)}：{len(rows)} 行")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--data-dir", default=os.path.join(here, "data"),
                    help="数据目录（默认脚本同级 data/）")
    args = ap.parse_args()
    data_dir = args.data_dir
    os.makedirs(data_dir, exist_ok=True)

    print(f"== 海龟看板·每日数据更新 @ {datetime.now():%Y-%m-%d %H:%M:%S} ==")
    print(f"数据目录：{data_dir}")
    total = 0
    for sym in SYMBOLS:
        print(f"-- {sym['name']} ({sym['ts_code']})")
        rows = fetch_full(sym)
        if not rows:
            continue
        total += append_new(data_dir, sym, rows)
    print(f"== 完成，本次共新增 {total} 行 ==")
    # 退出码 0，便于 CI 即便个别标的失败也继续
    sys.exit(0)


if __name__ == "__main__":
    main()
