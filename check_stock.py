import tushare as ts
ts.set_token('5786743e32ed0a3472d784b70cb7a2692caf675438701623112a2d2a')
pro = ts.pro_api()

# 查一下 00300.HK 是什么
df = pro.hk_basic(ts_code='00300.HK')
print(df.to_string())

# 查美的集团的港股信息
df2 = pro.hk_basic(ts_code='')
# 试试搜名字
print("\n--- Search for Midea HK ---")
# 直接用 stock_basic 找美的
df3 = pro.stock_basic(name='美的')
print(df3.to_string())
