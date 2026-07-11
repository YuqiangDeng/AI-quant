#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_task4_turtle_dashboard.py — 海龟交易法则·回测演示看板 生成器

读取 data/*.csv（真前复权日线），把数据内联进 HTML，
并嵌入纯 JS 海龟回测引擎（S1/S2/组合、N=ATR、Unit、2N止损、0.5N加仓、指标、Plotly 可视化），
输出自包含（仅同源引用 vendor/plotly.min.js）的 task4_turtle_dashboard.html。

用法：
  python gen_task4_turtle_dashboard.py
  python gen_task4_turtle_dashboard.py --data-dir data --out task4_turtle_dashboard.html
"""

import argparse
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

NAMES = {
    "688981.SH": "中芯国际A",
    "002594.SZ": "比亚迪",
    "600900.SH": "长江电力",
    "000333.SZ": "美的集团",
    "00981.HK": "中芯国际H",
}

# ---------------------------------------------------------------------------
# 读取数据
# ---------------------------------------------------------------------------
def load_data(data_dir):
    data = {}
    for fn in sorted(os.listdir(data_dir)):
        if not fn.lower().endswith(".csv"):
            continue
        if "qfq" not in fn.lower() and fn.lower() != "smic_hk_daily.csv":
            continue
        path = os.path.join(data_dir, fn)
        rows = []
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                try:
                    t = int(str(row["trade_date"]).replace("-", "").strip()[:8])
                    o = float(row["open"]); h = float(row["high"])
                    l = float(row["low"]); c = float(row["close"])
                except (ValueError, KeyError, TypeError):
                    continue
                rows.append([t, o, h, l, c])
        if not rows:
            continue
        rows.sort(key=lambda x: x[0])
        # 取首行 ts_code 作为标的代码
        code = None
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rr = csv.DictReader(f)
            for first in rr:
                code = first.get("ts_code")
                break
        if not code:
            code = fn
        label = NAMES.get(code, code or fn)
        data[code] = {"label": label, "rows": rows}
    return data


# ---------------------------------------------------------------------------
# JS 海龟回测引擎（作为字符串内联进 HTML）
# ---------------------------------------------------------------------------
ENGINE_JS = r"""
'use strict';
const RED='#E24B4A', GREEN='#1D9E75', BLUE='#378ADD', ORANGE='#BA7517', PURPLE='#7F77DD', GRAY='#94a3b8';

function rowsOf(code){ return SYMBOL_DATA[code] ? SYMBOL_DATA[code].rows : []; }
function filterRange(rows, start, end){
  return rows.filter(r => (!start || r[0]>=start) && (!end || r[0]<=end));
}
function mean(a){ if(!a.length) return 0; let s=0; for(const v of a) s+=v; return s/a.length; }
function std(a){ if(a.length<2) return 0; const m=mean(a); let s=0; for(const v of a) s+=(v-m)*(v-m); return Math.sqrt(s/(a.length-1)); }

function atrSeries(h,l,c,n){
  const m=h.length, tr=new Array(m).fill(NaN);
  for(let i=0;i<m;i++){
    tr[i] = (i===0) ? (h[i]-l[i]) : Math.max(h[i]-l[i], Math.abs(h[i]-c[i-1]), Math.abs(l[i]-c[i-1]));
  }
  const atr=new Array(m).fill(NaN);
  if(m>=n){
    let s=0; for(let i=0;i<n;i++) s+=tr[i];
    atr[n-1]=s/n;
    for(let i=n;i<m;i++) atr[i]=(atr[i-1]*(n-1)+tr[i])/n;
  }
  return atr;
}
function donchianHigh(h,p){
  const m=h.length, out=new Array(m).fill(null);
  for(let i=p;i<m;i++){ let mx=-Infinity; for(let j=i-p;j<i;j++) if(h[j]>mx) mx=h[j]; out[i]=mx; }
  return out;
}
function donchianLow(l,p){
  const m=l.length, out=new Array(m).fill(null);
  for(let i=p;i<m;i++){ let mn=Infinity; for(let j=i-p;j<i;j++) if(l[j]<mn) mn=l[j]; out[i]=mn; }
  return out;
}

function buyUnit(st, price, N, dir, i, params, rate, list, isAdd){
  const equityNow = st.cash + st.pos*price;
  let mag = Math.floor((equityNow*params.riskPct/100)/N);
  if(mag<=0) return;
  const sh = mag*dir;
  const cost = sh*price;
  const comm = Math.abs(cost)*rate;
  st.cash -= (cost+comm);
  st.pos += sh;
  st.costBasis += cost;
  st.openComm += comm;
  st.units += 1;
  st.lastEntry = price;
  st.avg = st.costBasis/st.pos;
  if(st.units===1){ st.entryIdx=i; st.entryPrice=price; }
  if(list) list.push({i:i, price:price, dir:dir});
}
function sellAll(st, price, i, reason, trades, rate){
  if(st.pos===0) return;
  const proceeds = st.pos*price;
  const comm = Math.abs(proceeds)*rate;
  st.cash += proceeds - comm;
  const pnl = (price - st.avg)*st.pos - (st.openComm + comm);
  trades.push({entryIdx:st.entryIdx, exitIdx:i, entryPrice:st.avg, exitPrice:price,
               shares:Math.abs(st.pos), pnl:pnl, reason:reason});
  st.pos=0; st.costBasis=0; st.openComm=0; st.units=0; st.lastEntry=0; st.avg=0; st.entryIdx=-1;
}

function simulate(rows, params, sys, weight, total0, allowShort){
  const m=rows.length;
  const o=rows.map(r=>r[1]), h=rows.map(r=>r[2]), l=rows.map(r=>r[3]), c=rows.map(r=>r[4]);
  const atr=atrSeries(h,l,c,params.n);
  const dh=donchianHigh(h,sys.entry);
  const dl=donchianLow(l,sys.exit);
  const eq0=total0*weight;
  let st={cash:eq0,pos:0,costBasis:0,openComm:0,units:0,lastEntry:0,avg:0,entryIdx:-1,entryPrice:0};
  const equity=new Array(m).fill(eq0);
  const trades=[], adds=[], entries=[];
  const rate=params.costOn?params.costRate:0;
  for(let i=0;i<m;i++){
    const N=atr[i];
    if(isNaN(N)) continue;
    if(st.pos===0){
      let dir=0;
      if(c[i]>dh[i]) dir=1;
      else if(allowShort && c[i]<dl[i]) dir=-1;
      if(dir!==0) buyUnit(st, c[i], N, dir, i, params, rate, entries, false);
    } else if(st.pos>0){
      if(c[i] >= st.lastEntry + params.addStep*N && st.units<params.maxUnits)
        buyUnit(st, c[i], N, 1, i, params, rate, adds, true);
      if(l[i] <= st.avg - params.stopMult*N)
        sellAll(st, st.avg - params.stopMult*N, i, '止损', trades, rate);
      else if(c[i] < dl[i])
        sellAll(st, c[i], i, '离场', trades, rate);
    } else {
      if(c[i] <= st.lastEntry - params.addStep*N && st.units<params.maxUnits)
        buyUnit(st, c[i], N, -1, i, params, rate, adds, true);
      if(h[i] >= st.avg + params.stopMult*N)
        sellAll(st, st.avg + params.stopMult*N, i, '止损', trades, rate);
      else if(c[i] > dh[i])
        sellAll(st, c[i], i, '离场', trades, rate);
    }
    equity[i] = st.cash + st.pos*c[i];
  }
  return {equity:equity, trades:trades, adds:adds, entries:entries};
}

function runBacktest(params){
  const rows = filterRange(rowsOf(params.code), params.start, params.end);
  const warm = Math.max(params.n, params.sysS1.entry, params.sysS1.exit, params.sysS2.entry, params.sysS2.exit)+1;
  if(rows.length < warm)
    return {error:'数据不足：当前区间仅 '+rows.length+' 个交易日，海龟需要至少 '+warm+' 日（含预热期）。请扩大时段或缩短周期。'};
  const total0=params.initCapital;
  let sims, weights;
  if(params.system==='S1'){ sims=[params.sysS1]; weights=[1]; }
  else if(params.system==='S2'){ sims=[params.sysS2]; weights=[1]; }
  else { sims=[params.sysS1, params.sysS2]; weights=[0.4,0.6]; }
  const m=rows.length;
  const combined=new Array(m).fill(0);
  let allTrades=[], allAdds=[], allEntries=[];
  for(let s=0;s<sims.length;s++){
    const r=simulate(rows, params, sims[s], weights[s], total0, params.allowShort);
    for(let i=0;i<m;i++) combined[i]+=r.equity[i];
    allTrades=allTrades.concat(r.trades.map(t=>(Object.assign({sys:s}, t))));
    allAdds=allAdds.concat(r.adds);
    allEntries=allEntries.concat(r.entries);
  }
  const ret=[];
  for(let i=1;i<m;i++) ret.push(combined[i]/combined[i-1]-1);
  const totalRet=combined[m-1]/combined[0]-1;
  const ann=Math.pow(combined[m-1]/combined[0], 252/m)-1;
  const rfD=params.rf/100/252;
  const mr=mean(ret), sd=std(ret);
  const sharpe = sd>0 ? (mr-rfD)/sd*Math.sqrt(252) : 0;
  let peak=combined[0], mdd=0;
  for(let i=0;i<m;i++){ if(combined[i]>peak)peak=combined[i]; const dd=(peak-combined[i])/peak; if(dd>mdd)mdd=dd; }
  let wins=0, gW=0, gL=0;
  allTrades.forEach(t=>{ if(t.pnl>0){wins++; gW+=t.pnl;} else gL+=-t.pnl; });
  const winRate = allTrades.length? wins/allTrades.length : 0;
  const avgWin = wins? gW/wins:0;
  const avgLoss = (allTrades.length-wins)? gL/(allTrades.length-wins):0;
  const profitFactor = avgLoss>0? avgWin/avgLoss : (gW>0? Infinity:0);
  const expectancy = winRate*avgWin - (1-winRate)*avgLoss;
  const bh=new Array(m); bh[0]=total0;
  for(let i=1;i<m;i++) bh[i]=total0*rows[i][4]/rows[0][4];
  const bhRet=bh[m-1]/bh[0]-1;
  const excess=totalRet-bhRet;
  return {rows, combined, bh, allTrades, allAdds, allEntries, total0,
    metrics:{totalRet, ann, sharpe, mdd, winRate, avgWin, avgLoss, profitFactor, expectancy,
             trades:allTrades.length, excess, rf:params.rf}};
}

// ---------------- 渲染 ----------------
const FONT={family:'-apple-system, "Segoe UI", "Microsoft YaHei", sans-serif', size:12, color:'#1f2d3d'};
function baseLayout(title, ytitle){
  return {title:{text:title, font:{size:14, color:'#1f2d3d'}}, font:FONT,
    paper_bgcolor:'#fff', plot_bgcolor:'#fff', margin:{l:55,r:20,t:40,b:40},
    xaxis:{gridcolor:'#eef2f6', zeroline:false}, yaxis:{gridcolor:'#eef2f6', zeroline:false, title:ytitle||''},
    legend:{orientation:'h', y:-0.18, font:{size:11}}, hovermode:'x unified'};
}
function render(res){
  if(res.error){ document.getElementById('charts').innerHTML='<div class="alert">'+res.error+'</div>';
    document.getElementById('metrics').innerHTML=''; document.getElementById('tradetable').innerHTML=''; return; }
  const rows=res.rows, dates=rows.map(r=>String(r[0]));
  const o=rows.map(r=>r[1]), h=rows.map(r=>r[2]), l=rows.map(r=>r[3]), c=rows.map(r=>r[4]);
  // 主图 K线 + 通道
  const tCandle={type:'candlestick', x:dates, open:o, high:h, low:l, close:c,
    increasing:{line:{color:RED}}, decreasing:{line:{color:GREEN}}, name:'K线'};
  const dh1=donchianHigh(h, P.sysS1.entry), dl1=donchianLow(l, P.sysS1.exit);
  const traces=[tCandle,
    {x:dates,y:dh1,mode:'lines',name:'S1上轨('+P.sysS1.entry+')',line:{color:BLUE,width:1}},
    {x:dates,y:dl1,mode:'lines',name:'S1下轨('+P.sysS1.exit+')',line:{color:BLUE,width:1,dash:'dot'}}];
  if(P.system==='S1S2'){
    const dh2=donchianHigh(h,P.sysS2.entry), dl2=donchianLow(l,P.sysS2.exit);
    traces.push({x:dates,y:dh2,mode:'lines',name:'S2上轨('+P.sysS2.entry+')',line:{color:PURPLE,width:1,dash:'dash'}});
    traces.push({x:dates,y:dl2,mode:'lines',name:'S2下轨('+P.sysS2.exit+')',line:{color:PURPLE,width:1,dash:'dashdot'}});
  }
  const bx=[],by=[],ax=[],ay=[],sx=[],sy=[];
  res.allEntries.forEach(e=>{ bx.push(dates[e.i]); by.push(e.price); });
  res.allAdds.forEach(a=>{ ax.push(dates[a.i]); ay.push(a.price); });
  res.allTrades.forEach(t=>{ sx.push(dates[t.exitIdx]); sy.push(t.exitPrice); });
  traces.push({x:bx,y:by,mode:'markers',name:'买入',marker:{symbol:'circle',size:9,color:RED,line:{color:'#fff',width:1}}});
  traces.push({x:ax,y:ay,mode:'markers',name:'加仓',marker:{symbol:'circle',size:7,color:ORANGE}});
  traces.push({x:sx,y:sy,mode:'markers',name:'卖出',marker:{symbol:'x',size:9,color:GREEN}});
  Plotly.newPlot('chartMain', traces, baseLayout('价格 / 唐奇安通道 / 交易点位', '价格'),
    {responsive:true, displayModeBar:false});
  // 资金曲线
  const eqN=res.combined.map(v=>v/res.total0), bhN=res.bh.map(v=>v/res.total0);
  Plotly.newPlot('chartEquity',[
    {x:dates,y:eqN,mode:'lines',name:'策略净值',line:{color:BLUE,width:1.6}},
    {x:dates,y:bhN,mode:'lines',name:'买入持有',line:{color:GRAY,width:1.2,dash:'dash'}}],
    baseLayout('资金曲线（净值，起点1.0）'), {responsive:true, displayModeBar:false});
  // 回撤
  let pk=res.combined[0]; const dd=res.combined.map(v=>{ if(v>pk)pk=v; return (pk-v)/pk; });
  Plotly.newPlot('chartDD',[{x:dates,y:dd,type:'scatter',fill:'tozeroy',name:'回撤',
    line:{color:RED,width:1}}], baseLayout('回撤曲线', '回撤'), {responsive:true, displayModeBar:false});
  // N
  const atr=atrSeries(h,l,c,P.n);
  Plotly.newPlot('chartN',[{x:dates,y:atr,mode:'lines',name:'N(ATR'+P.n+')',line:{color:ORANGE,width:1}}],
    baseLayout('N（真实波幅均值 = ATR'+P.n+'）'), {responsive:true, displayModeBar:false});
  // 指标卡
  const M=res.metrics;
  const cards=[
    ['累计收益率', (M.totalRet*100).toFixed(2)+'%', cls(M.totalRet)],
    ['年化收益率', (M.ann*100).toFixed(2)+'%', cls(M.ann)],
    ['夏普比率', M.sharpe.toFixed(2), cls(M.sharpe)],
    ['最大回撤 MDD', (M.mdd*100).toFixed(2)+'%', M.mdd<0.1?'good':(M.mdd<0.2?'mid':'bad')],
    ['胜率', (M.winRate*100).toFixed(1)+'%', ''],
    ['盈亏比', (isFinite(M.profitFactor)?M.profitFactor.toFixed(2):'∞'), ''],
    ['期望收益', (M.expectancy/res.total0*100).toFixed(2)+'%', cls(M.expectancy)],
    ['交易次数', String(M.trades), ''],
    ['相对买入持有超额', (M.excess*100).toFixed(2)+'%', cls(M.excess)],
  ];
  document.getElementById('metrics').innerHTML = cards.map(c=>
    '<div class="card '+c[2]+'"><div class="k">'+c[0]+'</div><div class="v">'+c[1]+'</div></div>').join('');
  // 交易表
  let th='<table class="t"><thead><tr><th>#</th><th>买入日</th><th>卖出日</th><th>买入价</th><th>卖出价</th><th>股数</th><th>净利润</th><th>收益率</th><th>持仓天数</th><th>类型</th></tr></thead><tbody>';
  res.allTrades.slice().sort((a,b)=>a.exitIdx-b.exitIdx).forEach((t,i)=>{
    const days=rows[t.exitIdx][0]-rows[t.entryIdx][0];
    const ret=t.pnl/(t.entryPrice*t.shares);
    th+='<tr><td>'+(i+1)+'</td><td>'+rows[t.entryIdx][0]+'</td><td>'+rows[t.exitIdx][0]+
      '</td><td>'+t.entryPrice.toFixed(2)+'</td><td>'+t.exitPrice.toFixed(2)+'</td><td>'+t.shares+
      '</td><td class="'+(t.pnl>=0?'pos':'neg')+'">'+(t.pnl>=0?'+':'')+t.pnl.toFixed(0)+
      '</td><td class="'+(ret>=0?'pos':'neg')+'">'+(ret*100).toFixed(2)+'%</td><td>'+days+
      '</td><td>'+(t.reason==='止损'?'<span class="badge bad">止损</span>':'<span class="badge">离场</span>')+'</td></tr>';
  });
  th+='</tbody></table>';
  document.getElementById('tradetable').innerHTML = th;
}
function cls(v){ return v>0?'good':(v<0?'bad':'mid'); }

// ---------------- 参数收集 / 事件 ----------------
// 注意：SYMBOL_DATA 由数据脚本（<script>var SYMBOL_DATA=...</script>）注入为全局，此处不可再声明，否则会遮蔽。
let P = {};
function readParams(){
  const g=id=>document.getElementById(id).value;
  const sys=g('system');
  let e1=20,x1=10,e2=55,x2=20;
  if(sys==='S1'){ e1=+g('entryP')||20; x1=+g('exitP')||10; }
  else if(sys==='S2'){ e2=+g('entryP')||55; x2=+g('exitP')||20; }
  P = {
    code: g('symbol'),
    system: sys,
    start: g('start')? +g('start') : null,
    end: g('end')? +g('end') : null,
    n: +g('nPeriod')||20,
    riskPct: +g('riskPct')||1,
    initCapital: +g('capital')||1000000,
    addStep: +g('addStep')||0.5,
    maxUnits: +g('maxUnits')||4,
    stopMult: +g('stopMult')||2,
    allowShort: document.getElementById('allowShort').checked,
    costOn: document.getElementById('costOn').checked,
    costRate: (+g('costRate')||3)/10000,  // UI 单位：万分之（3 = 0.03%）
    rf: +g('rf')||1.79,
    sysS1:{entry:e1, exit:x1}, sysS2:{entry:e2, exit:x2},
  };
}
function run(){
  readParams();
  const res=runBacktest(P);
  render(res);
}
function refreshSymbols(){
  const sel=document.getElementById('symbol');
  const cur=sel.value;
  sel.innerHTML='';
  Object.keys(SYMBOL_DATA).forEach(code=>{
    const o=document.createElement('option');
    o.value=code; o.textContent=SYMBOL_DATA[code].label+' ('+code+')';
    sel.appendChild(o);
  });
  if(cur && SYMBOL_DATA[cur]) sel.value=cur;
}
function setRange(years){
  // 用当前标的数据计算起点
  const rows=rowsOf(document.getElementById('symbol').value);
  if(!rows.length) return;
  const last=rows[rows.length-1][0];
  const startY=Math.floor(last/10000)-years;
  const start=startY*10000+101;
  document.getElementById('start').value=start;
  document.getElementById('end').value=last;
}
function importCSV(text){
  const lines=text.split(/\r?\n/).filter(x=>x.trim());
  if(lines.length<2){ alert('CSV 为空'); return; }
  const hdr=lines[0].split(','); const idx={};
  hdr.forEach((hh,i)=>idx[hh.trim()]=i);
  const dk = idx['trade_date']!==undefined?'trade_date':(idx['date']!==undefined?'date':null);
  if(dk===null || ['open','high','low','close'].some(k=>idx[k]===undefined)){ alert('需含 trade_date/open/high/low/close 字段'); return; }
  const f0=lines[1].split(',');
  const code = (idx['ts_code']!==undefined)? f0[idx['ts_code']] : ('IMPORT'+Object.keys(SYMBOL_DATA).length);
  const rows=[];
  for(let i=1;i<lines.length;i++){
    const f=lines[i].split(',');
    const t=parseInt(String(f[idx[dk]]).replace(/-/g,''));
    if(isNaN(t)) continue;
    rows.push([t, parseFloat(f[idx['open']]), parseFloat(f[idx['high']]), parseFloat(f[idx['low']]), parseFloat(f[idx['close']])]);
  }
  rows.sort((a,b)=>a[0]-b[0]);
  SYMBOL_DATA[code]={label:code+' (导入)', rows:rows};
  refreshSymbols();
  document.getElementById('symbol').value=code;
  alert('已导入 '+code+'，共 '+rows.length+' 行。可直接运行回测。');
}
"""

# ---------------------------------------------------------------------------
# HTML 外壳
# ---------------------------------------------------------------------------
HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>海龟交易法则 · 回测演示看板</title>
<script src="vendor/plotly.min.js"></script>
<style>
  :root{ --bg:#f5f7fa; --card:#fff; --bd:#e2e8f0; --txt:#1f2d3d; --mut:#64748b; --blue:#185FA5; }
  *{box-sizing:border-box;}
  body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--txt);font-size:13px;}
  header{background:linear-gradient(90deg,#0C447C,#185FA5);color:#fff;padding:14px 22px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
  header h1{font-size:17px;margin:0;font-weight:600;}
  .badge-date{background:rgba(255,255,255,.18);padding:4px 10px;border-radius:8px;font-size:12px;}
  .wrap{display:flex;gap:16px;padding:16px;align-items:flex-start;}
  .panel{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;width:300px;flex:0 0 300px;}
  .panel h2{font-size:14px;margin:0 0 10px;color:var(--blue);}
  .row{margin-bottom:10px;}
  .row label{display:block;font-size:12px;color:var(--mut);margin-bottom:3px;}
  .row input,.row select{width:100%;padding:6px 8px;border:1px solid var(--bd);border-radius:8px;font-size:13px;}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;}
  .chk{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--mut);margin-bottom:6px;}
  .btn{width:100%;padding:9px;border:none;border-radius:9px;background:var(--blue);color:#fff;font-size:14px;cursor:pointer;margin-top:4px;}
  .btn:hover{background:#0C447C;}
  .quick{display:flex;gap:6px;margin-top:4px;}
  .quick button{flex:1;padding:5px;font-size:11px;border:1px solid var(--bd);background:#fff;border-radius:7px;cursor:pointer;color:var(--mut);}
  .quick button:hover{border-color:var(--blue);color:var(--blue);}
  .main{flex:1;min-width:0;display:flex;flex-direction:column;gap:14px;}
  .metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;}
  .card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;}
  .card .k{font-size:11px;color:var(--mut);}
  .card .v{font-size:18px;font-weight:600;margin-top:2px;}
  .card.good .v{color:#1D9E75;} .card.bad .v{color:#E24B4A;} .card.mid .v{color:#BA7517;}
  .chart{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:8px;}
  #metrics .card{border-left:3px solid var(--bd);}
  #metrics .card.good{border-left-color:#1D9E75;} #metrics .card.bad{border-left-color:#E24B4A;} #metrics .card.mid{border-left-color:#BA7517;}
  table.t{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px;}
  table.t th,table.t td{border-bottom:1px solid var(--bd);padding:6px 8px;text-align:right;}
  table.t th{color:var(--mut);font-weight:500;background:#f8fafc;}
  .pos{color:#E24B4A;} .neg{color:#1D9E75;} /* 涨红跌绿 */
  .badge{display:inline-block;padding:1px 7px;border-radius:6px;background:#eef2f6;color:var(--mut);font-size:11px;}
  .badge.bad{background:#fdeaea;color:#E24B4A;}
  .alert{background:#fff5f5;border:1px solid #f0c0c0;color:#a32d2d;padding:14px;border-radius:10px;}
  .note{font-size:11px;color:var(--mut);line-height:1.5;margin-top:8px;}
</style>
</head>
<body>
<header>
  <h1>🐢 海龟交易法则 · 回测演示看板</h1>
  <span class="badge-date" id="dataBadge">数据加载中…</span>
  <span style="margin-left:auto;font-size:12px;opacity:.9;">唐奇安突破 · N=ATR · Unit头寸 · 2N止损 · 0.5N加仓</span>
</header>
<div class="wrap">
  <div class="panel">
    <h2>参数配置</h2>
    <div class="row"><label>标的</label><select id="symbol"></select></div>
    <div class="row"><label>时段（起 / 止，YYYYMMDD）</label>
      <div class="grid2"><input id="start" placeholder="全部"><input id="end" placeholder="全部"></div>
      <div class="quick">
        <button onclick="setRange(1)">近1年</button>
        <button onclick="setRange(3)">近3年</button>
        <button onclick="document.getElementById('start').value='';document.getElementById('end').value='';">全部</button>
      </div>
    </div>
    <div class="row"><label>系统</label>
      <select id="system">
        <option value="S1">S1（20日突破 / 10日离场）</option>
        <option value="S2">S2（55日突破 / 20日离场）</option>
        <option value="S1S2" selected>S1+S2 组合（40% / 60%）</option>
      </select>
    </div>
    <div class="row grid2">
      <div><label>入场周期</label><input id="entryP" type="number" value="20"></div>
      <div><label>离场周期</label><input id="exitP" type="number" value="10"></div>
    </div>
    <div class="row grid2">
      <div><label>N周期(ATR)</label><input id="nPeriod" type="number" value="20"></div>
      <div><label>风险比例%</label><input id="riskPct" type="number" value="1" step="0.1"></div>
    </div>
    <div class="row"><label>初始资金(元)</label><input id="capital" type="number" value="1000000"></div>
    <div class="row grid2">
      <div><label>加仓间距×N</label><input id="addStep" type="number" value="0.5" step="0.1"></div>
      <div><label>最大单位数</label><input id="maxUnits" type="number" value="4"></div>
    </div>
    <div class="row"><label>止损倍数×N</label><input id="stopMult" type="number" value="2" step="0.1"></div>
    <div class="row grid2">
      <div><label>无风险利率rf%</label><input id="rf" type="number" value="1.79" step="0.01"></div>
      <div><label>手续费(万分之)</label><input id="costRate" type="number" value="3"></div>
    </div>
    <label class="chk"><input type="checkbox" id="allowShort"> 允许做空（对称逻辑）</label>
    <label class="chk"><input type="checkbox" id="costOn" checked> 计入交易成本</label>
    <button class="btn" onclick="run()">运行回测</button>
    <div class="row" style="margin-top:10px;"><label>导入最新CSV（覆盖/新增标的）</label>
      <input type="file" id="csvFile" accept=".csv"></div>
    <div class="note">数据更新：本地运行 <code>update_turtle_data.py</code> 追加新交易日；或点上方导入最新CSV，即可用最新完整数据回测。</div>
  </div>
  <div class="main">
    <div id="metrics" class="metrics"></div>
    <div class="chart" id="charts"><div id="chartMain" style="height:380px;"></div></div>
    <div class="chart" id="chartEquity" style="height:300px;"></div>
    <div class="chart" id="chartDD" style="height:240px;"></div>
    <div class="chart" id="chartN" style="height:220px;"></div>
    <div class="chart" id="tradetable"></div>
  </div>
</div>
"""

HTML_TAIL = """
<script>
// 末交易日徽标（SYMBOL_DATA 已由上方数据脚本以 var 注入，此处不可再用 const 声明，否则浏览器抛 SyntaxError）
(function(){
  let last=0; Object.values(SYMBOL_DATA).forEach(d=>{ if(d.rows.length){ const t=d.rows[d.rows.length-1][0]; if(t>last)last=t; } });
  document.getElementById('dataBadge').textContent = '数据最后交易日：' + (last||'—');
  refreshSymbols();
  document.getElementById('csvFile').addEventListener('change', function(e){
    const f=e.target.files[0]; if(!f) return; const r=new FileReader();
    r.onload=function(){ importCSV(r.result); }; r.readAsText(f, 'utf-8');
  });
  run();
})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(HERE, "data"))
    ap.add_argument("--out", default=os.path.join(HERE, "task4_turtle_dashboard.html"))
    args = ap.parse_args()

    data = load_data(args.data_dir)
    if not data:
        raise SystemExit("未在 " + args.data_dir + " 找到 qfq CSV 数据")
    data_js = json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    html = (HTML_HEAD
            + "<script>var SYMBOL_DATA = " + data_js + ";</script>\n"
            + "<script>" + ENGINE_JS + "</script>\n"
            + HTML_TAIL.replace("__DATA__", data_js))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("已生成：", args.out, os.path.getsize(args.out), "bytes")
    print("标的数：", len(data), "->", {c: len(v["rows"]) for c, v in data.items()})


if __name__ == "__main__":
    main()
