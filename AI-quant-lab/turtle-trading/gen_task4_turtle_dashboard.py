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
// YYYYMMDD(整数) -> "YYYY-MM-DD"（用于坐标/表格显示，便于阅读）
function fmtDate(t){ const s=String(t); return s.length>=8 ? s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8) : s; }
function parseDate(t){ const s=String(t); return new Date(+s.slice(0,4), +s.slice(4,6)-1, +s.slice(6,8)); }
function daysBetween(a,b){ return Math.round((parseDate(b)-parseDate(a))/86400000); }
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
  const unitsSeries=new Array(m).fill(0);
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
    unitsSeries[i] = st.units;
  }
  return {equity:equity, trades:trades, adds:adds, entries:entries, unitsSeries:unitsSeries};
}

function runBacktest(params){
  const rows = filterRange(rowsOf(params.code), params.start, params.end);
  const warm = Math.max(params.n, params.sysS1.entry, params.sysS1.exit, params.sysS2.entry, params.sysS2.exit)+1;
  if(rows.length < warm)
    return {error:'数据不足：当前区间仅 '+rows.length+' 个交易日，海龟需要至少 '+warm+' 日（含预热期）。请扩大时段或缩短周期。'};
  const total0=params.initCapital;
  let sims, weights;
  if(params.system==='S1'){ sims=[params.sysS1]; weights=[1]; }
  else { sims=[params.sysS2]; weights=[1]; }
  const m=rows.length;
  const combined=new Array(m).fill(0);
  const sysMaxUnits=new Array(m).fill(0);  // 每日各子系统(maxUnits≤4)中的最大持仓单位数
  let allTrades=[], allAdds=[], allEntries=[];
  for(let s=0;s<sims.length;s++){
    const r=simulate(rows, params, sims[s], weights[s], total0, params.allowShort);
    for(let i=0;i<m;i++){ combined[i]+=r.equity[i]; if(r.unitsSeries[i]>sysMaxUnits[i]) sysMaxUnits[i]=r.unitsSeries[i]; }
    allTrades=allTrades.concat(r.trades.map(t=>(Object.assign({sys:s}, t))));
    allAdds=allAdds.concat(r.adds);
    allEntries=allEntries.concat(r.entries);
  }
  // 峰值/平均持有单位（海龟 4 单位上限针对所选子系统）
  let maxUnitsHeld=0, sumUnits=0, cntUnits=0;
  for(let i=0;i<m;i++){ if(sysMaxUnits[i]>maxUnitsHeld)maxUnitsHeld=sysMaxUnits[i]; if(sysMaxUnits[i]>0){sumUnits+=sysMaxUnits[i];cntUnits++;} }
  const avgUnits = cntUnits? sumUnits/cntUnits : 0;
  let maxLossPct=0;
  allTrades.forEach(t=>{ const r=t.pnl/(t.entryPrice*t.shares); if(r<maxLossPct)maxLossPct=r; });
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
             trades:allTrades.length, excess, rf:params.rf,
             maxUnitsHeld, avgUnits, maxLossPct}};
}

// ---------------- 渲染 ----------------
const FONT={family:'-apple-system, "Segoe UI", "Microsoft YaHei", sans-serif', size:12, color:'#1f2d3d'};
function baseLayout(title, ytitle){
  return {title:{text:title, font:{size:14, color:'#1f2d3d'}}, font:FONT,
    paper_bgcolor:'#fff', plot_bgcolor:'#fff', margin:{l:55,r:20,t:40,b:40},
    xaxis:{type:'date', gridcolor:'#eef2f6', zeroline:false}, yaxis:{gridcolor:'#eef2f6', zeroline:false, title:ytitle||''},
    legend:{orientation:'h', y:-0.18, font:{size:11}}, hovermode:'x unified'};
}
function render(res){
  if(res.error){ document.getElementById('charts').innerHTML='<div class="alert">'+res.error+'</div>';
    document.getElementById('metrics').innerHTML=''; document.getElementById('tradetable').innerHTML=''; return; }
  const rows=res.rows, dates=rows.map(r=>fmtDate(r[0]));
  const o=rows.map(r=>r[1]), h=rows.map(r=>r[2]), l=rows.map(r=>r[3]), c=rows.map(r=>r[4]);
  // 主图 K线 + 通道
  const tCandle={type:'candlestick', x:dates, open:o, high:h, low:l, close:c,
    increasing:{line:{color:RED}}, decreasing:{line:{color:GREEN}}, name:'K线'};
  const dh1=donchianHigh(h, P.sysS1.entry), dl1=donchianLow(l, P.sysS1.exit);
  const traces=[tCandle,
    {x:dates,y:dh1,mode:'lines',name:'S1上轨('+P.sysS1.entry+')',line:{color:BLUE,width:1}},
    {x:dates,y:dl1,mode:'lines',name:'S1下轨('+P.sysS1.exit+')',line:{color:BLUE,width:1,dash:'dot'}}];
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
    ['峰值持有单位(每系统≤4)', String(M.maxUnitsHeld), M.maxUnitsHeld>4?'bad':''],
    ['平均持有单位', M.avgUnits.toFixed(2), ''],
    ['单笔最大亏损', (M.maxLossPct*100).toFixed(2)+'%', M.maxLossPct<-0.04?'bad':''],
  ];
  document.getElementById('metrics').innerHTML = cards.map(c=>
    '<div class="card '+c[2]+'"><div class="k">'+c[0]+'</div><div class="v">'+c[1]+'</div></div>').join('');
  // 交易表
  let th='<table class="t"><thead><tr><th>#</th><th>买入日</th><th>卖出日</th><th>买入价</th><th>卖出价</th><th>股数</th><th>净利润</th><th>收益率</th><th>持仓天数</th><th>类型</th></tr></thead><tbody>';
  res.allTrades.slice().sort((a,b)=>a.exitIdx-b.exitIdx).forEach((t,i)=>{
    const days=daysBetween(rows[t.entryIdx][0], rows[t.exitIdx][0]);
    const ret=t.pnl/(t.entryPrice*t.shares);
    th+='<tr><td>'+(i+1)+'</td><td>'+fmtDate(rows[t.entryIdx][0])+'</td><td>'+fmtDate(rows[t.exitIdx][0])+
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
// 注意：SYMBOL_DATA 由数据脚本以 var 注入为全局，此处不可再声明，否则会遮蔽。
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
  /* 系统说明 */
  .btn-about{margin-left:14px;padding:6px 12px;border:1px solid rgba(255,255,255,.5);background:rgba(255,255,255,.12);color:#fff;border-radius:8px;font-size:12px;cursor:pointer;}
  .btn-about:hover{background:rgba(255,255,255,.25);}
  .about{max-width:1100px;margin:0 auto 30px;padding:0 16px;}
  .about h2{color:var(--blue);font-size:18px;margin:18px 0 12px;}
  .about h3{color:var(--blue);font-size:15px;margin:18px 0 8px;border-left:4px solid var(--blue);padding-left:8px;}
  .elems{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;}
  .elem{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px;}
  .elem .et{font-weight:600;color:var(--blue);margin-bottom:4px;}
  .elem .ed{font-size:12px;color:var(--mut);line-height:1.5;}
  .formula{background:#0C447C;color:#EAF2FB;border-radius:10px;padding:12px 16px;font-size:13px;line-height:1.9;font-family:"SFMono-Regular",Consolas,monospace;}
  .ed2{font-size:13px;color:var(--txt);line-height:1.7;margin-top:8px;}
  .risk{background:#fff5f5;border:1px solid #f0c0c0;border-radius:10px;padding:12px 18px;font-size:13px;line-height:1.8;}
  .risk b{color:#E24B4A;}
  .flow{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px;overflow-x:auto;}
</style>
</head>
<body>
<header>
  <h1>🐢 海龟交易法则 · 回测演示看板</h1>
  <span class="badge-date" id="dataBadge">数据加载中…</span>
  <span style="margin-left:auto;font-size:12px;opacity:.9;">唐奇安突破 · N=ATR · Unit头寸 · 2N止损 · 0.5N加仓</span>
  <button class="btn-about" onclick="toggleAbout()">📖 海龟系统说明</button>
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
        <option value="S1" selected>S1（20日突破 / 10日离场）</option>
        <option value="S2">S2（55日突破 / 20日离场）</option>
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
    <div class="note">数据来源：已内置 5 只标的（比亚迪 / 美的 / 长江电力 / 中芯A / 中芯H）的前复权日线，由 <code>update_turtle_data.py</code> 每日增量更新。选择标的与时段后点“运行回测”即可。</div>
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

<section id="about" class="about" style="display:none;">
  <h2>🐢 海龟交易法则 · 完整系统说明</h2>

  <h3>一、五大核心要素</h3>
  <div class="elems">
    <div class="elem"><div class="et">① 市场选择</div><div class="ed">只交易流动性充足、波动足够的市场；ATR 衡量波动，太小不值得交易。</div></div>
    <div class="elem"><div class="et">② 头寸规模</div><div class="ed">Unit = 账户资金×1% ÷ ATR；波动大少买、小多买，风险归一化。</div></div>
    <div class="elem"><div class="et">③ 入场规则</div><div class="ed">唐奇安突破：价格创 N 日新高即入场（通道默认 20 日）。</div></div>
    <div class="elem"><div class="et">④ 止损规则</div><div class="ed">持仓均价 − 2×ATR 被跌破，立即全部平仓止损，纪律执行。</div></div>
    <div class="elem"><div class="et">⑤ 离场规则</div><div class="ed">价格跌破过去 M 日最低价即卖出（M 默认 10 日）。</div></div>
  </div>

  <h3>二、ATR 计算公式与含义</h3>
  <div class="formula">
    TR<sub>t</sub> = max( H<sub>t</sub>−L<sub>t</sub> , |H<sub>t</sub>−C<sub>t−1</sub>| , |L<sub>t</sub>−C<sub>t−1</sub>| )<br>
    ATR<sub>t</sub> = ( ATR<sub>t−1</sub>×(N−1) + TR<sub>t</sub> ) / N &nbsp;（N 日 Wilder 平滑，首值取前 N 日 TR 均值）
  </div>
  <div class="ed2">
    <b>ATR = 平均真实波幅</b>，代表股票近期每天大致波动多少钱。<b>越大→波动越剧烈→单位股数越少</b>（同样 1% 风险对应更少股数），这正是海龟"用波动定仓位"的精髓。<br>
    • <b>正常波动</b>：开≈昨收，TR 由当日振幅主导。<br>
    • <b>跳空高开</b>：开>昨收，|高−昨收| 主导 TR，常现利好。<br>
    • <b>跳空低开</b>：开<昨收，|低−昨收| 主导 TR，常现利空。<br>
    <span style="color:var(--mut)">注：TR 通过 |高−昨收|、|低−昨收| 两项自动把跳空计入波动，这是普通振幅(H−L)做不到的。</span>
  </div>

  <h3>三、头寸规模与加仓（金字塔）</h3>
  <div class="formula">
    每单位风险金额 = 账户资金 × 风险比例（默认 1%）<br>
    一个单位(可买股数) = 每单位风险金额 ÷ ATR<br>
    加仓：入场后价格每较上一单位 +0.5×ATR 再加 1 单位，最多 4 单位。
  </div>

  <h3>四、风险控制纪律（必须严格执行）</h3>
  <ul class="risk">
    <li>单个股票最多买入 <b>4 个单位</b>（引擎硬性封顶）。</li>
    <li>高度相关市场（如中芯 A 与中芯 H）合计不超过 <b>6 个单位</b>。</li>
    <li>同一方向（多/空）所有头寸合计不超过 <b>12 个单位</b>。</li>
    <li>账户总风险不超过 <b>12%</b>（单位数×2% 止损约束）。</li>
    <li>触发止损信号必须 <b>立即执行</b>，不得犹豫、不得摊平。</li>
    <li><b>必须严格执行纪律</b>——系统是机械的，主观干预是亏损根源。</li>
  </ul>

  <h3>五、海龟交易法则流程图</h3>
  <div class="flow">
  <svg viewBox="0 0 680 640" width="100%" style="max-width:720px;display:block;margin:0 auto;">
    <defs>
      <marker id="ar" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto">
        <path d="M0,0 L10,5 L0,10 z" fill="#94a3b8"/>
      </marker>
    </defs>
    <g font-family="-apple-system,'Segoe UI','Microsoft YaHei',sans-serif">
      <rect x="120" y="58" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="80" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">① 加载已存储股价数据</text>
      <text x="340" y="97" text-anchor="middle" font-size="11" fill="#64748b">OHLCV 日线（前复权）</text>
      <line x1="340" y1="104" x2="340" y2="114" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="116" width="440" height="60" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="138" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">② 参数面板</text>
      <text x="340" y="158" text-anchor="middle" font-size="11" fill="#64748b">通道周期 · ATR(N) · M离场 · 账户资金 · 风险比例%</text>
      <line x1="340" y1="176" x2="340" y2="186" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="188" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="210" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">③ 计算高低价格通道</text>
      <text x="340" y="227" text-anchor="middle" font-size="11" fill="#64748b">Donchian：上轨 = N日最高 / 下轨 = M日最低</text>
      <line x1="340" y1="234" x2="340" y2="244" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="246" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="268" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">④ 计算 ATR（N 日）</text>
      <text x="340" y="285" text-anchor="middle" font-size="11" fill="#64748b">Wilder 平滑真实波幅 = 波动强度</text>
      <line x1="340" y1="292" x2="340" y2="302" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="304" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="326" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">⑤ 生成交易信号</text>
      <text x="340" y="343" text-anchor="middle" font-size="11" fill="#64748b">突破 N 日最高 → 买 ｜ 跌破 M 日最低 → 卖</text>
      <line x1="340" y1="350" x2="340" y2="360" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="362" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="384" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">⑥ 入场：买入 1 单位</text>
      <text x="340" y="401" text-anchor="middle" font-size="11" fill="#64748b">Unit = 账户资金 × 1% ÷ ATR</text>
      <line x1="340" y1="408" x2="340" y2="418" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="420" width="440" height="128" rx="10" fill="#F3F8FF" stroke="#185FA5" stroke-width="1.5" stroke-dasharray="6 4"/>
      <text x="340" y="444" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">⑦ 持仓监控循环</text>
      <text x="150" y="470" font-size="12" fill="#1f2d3d">• 加仓：价格每 +0.5×ATR 加 1 单位（≤ 4 单位）</text>
      <text x="150" y="496" font-size="12" fill="#1f2d3d">• 止损：价格 ≤ 均价 − 2×ATR → 立即平仓</text>
      <text x="150" y="522" font-size="12" fill="#1f2d3d">• 离场：价格 &lt; M 日最低 → 卖出</text>
      <line x1="340" y1="548" x2="340" y2="558" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#ar)"/>

      <rect x="120" y="560" width="440" height="46" rx="10" fill="#EAF2FB" stroke="#185FA5" stroke-width="1.5"/>
      <text x="340" y="582" text-anchor="middle" font-size="14" font-weight="600" fill="#1f2d3d">⑧ 模拟交易与回测</text>
      <text x="340" y="599" text-anchor="middle" font-size="11" fill="#64748b">量化指标汇报 + 可视化（价格/通道/买卖信号）</text>
    </g>
  </svg>
  </div>
  <div class="ed2" style="color:var(--mut);">注：以上为简化流水线流程图；含决策分支（空仓/持仓、止损/离场/加仓判定）的完整 Mermaid 流程图见规格文件 <code>task4_turtle_trading_spec_v2.md</code>。</div>
</section>
"""

HTML_TAIL = """
<script>
function toggleAbout(){ var a=document.getElementById('about'); a.style.display = (a.style.display==='none'||a.style.display==='')?'block':'none'; }
// 末交易日徽标（SYMBOL_DATA 已由上方数据脚本以 var 注入，此处不可再用 const 声明，否则浏览器抛 SyntaxError）
(function(){
  let last=0; Object.values(SYMBOL_DATA).forEach(d=>{ if(d.rows.length){ const t=d.rows[d.rows.length-1][0]; if(t>last)last=t; } });
  document.getElementById('dataBadge').textContent = '数据最后交易日：' + (last||'—');
  refreshSymbols();
  run();
})();
</script>
<script>window.__BASE="../";</script>
<script src="../assets/back.js"></script>
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
