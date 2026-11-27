# -*- coding: utf-8 -*-
"""
可转债工作台 · 每日抓取脚本（GitHub Actions 每个交易日约 08:30 北京时间运行）
1) 东方财富 ulist 接口 → 13 只转债 + 13 只正股 的最新价/涨跌幅（失败自动切腾讯行情）
2) 东方财富公告接口 → 13 只正股近 14 天的 赎回/下修/回售/评级/兑付 等公告
3) 东方财富数据中心 → 转股价值/转股溢价率（尽力获取，失败则保留旧值）
输出 data.json，页面打开时自动加载。
"""
import re, json, time, datetime, requests

TZ = datetime.timezone(datetime.timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer": "https://quote.eastmoney.com/"}

# (转债代码, 转债名, 正股代码, 正股名)
BONDS = [
    ("118077", "莱特转债", "688150", "莱特光电"),
    ("127056", "中特转债", "000708", "中信特钢"),
    ("127040", "国泰转债", "002091", "江苏国泰"),
    ("127049", "希望转2", "000876", "新希望"),
    ("127047", "帝欧转债", "002798", "帝欧水华"),
    ("127050", "麒麟转债", "002984", "森麒麟"),
    ("127045", "牧原转债", "002714", "牧原股份"),
    ("113691", "和邦转债", "603077", "和邦生物"),
    ("123107", "温氏转债", "300498", "温氏股份"),
    ("118076", "先锋转债", "688605", "先锋精科"),
    ("113058", "友发转债", "601686", "友发集团"),
    ("127061", "美锦转债", "000723", "美锦能源"),
    ("118070", "南芯转债", "688484", "南芯科技"),
]
ANN_KW = re.compile(r"赎回|下修|向下修正|价格修正|转股价|回售|评级|付息|兑付|到期|摘牌|募集资金改变用途")
ANN_DAYS = 14

def b_secid(code):  return ("1." if code.startswith(("11", "13")) else "0.") + code
def s_secid(code):  return ("1." if code[0] == "6" else "0.") + code

def em_quotes():
    ids = ",".join([b_secid(b[0]) for b in BONDS] + [s_secid(b[2]) for b in BONDS])
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&fields=f2,f3,f12&secids=" + ids
    j = requests.get(url, headers=UA, timeout=15).json()
    diff = (j.get("data") or {}).get("diff") or []
    if isinstance(diff, dict): diff = list(diff.values())
    out = {}
    for o in diff:
        try:
            p, g = float(o["f2"]), float(o["f3"])
        except (TypeError, ValueError, KeyError):
            continue
        out[str(o["f12"])] = {"p": p, "chg": g}
    if not out: raise RuntimeError("em empty")
    return out

def tx_quotes():
    qs = ",".join(("sh" if b[0].startswith("11") else "sz") + b[0] for b in BONDS)
    r = requests.get("https://qt.gtimg.cn/q=" + qs, headers=UA, timeout=15)
    r.encoding = "gbk"
    out = {}
    for m in re.finditer(r'v_(?:sh|sz)(\d{6})="([^"]*)"', r.text):
        a = m.group(2).split("~")
        try: out[m.group(1)] = {"p": float(a[3]), "chg": float(a[32])}
        except (ValueError, IndexError): pass
    if not out: raise RuntimeError("tx empty")
    return out

def em_premium():
    """转股价值/溢价率（数据中心可转债表，字段名多候选防御）"""
    codes = ",".join('"%s"' % b[0] for b in BONDS)
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    params = {"reportName": "RPT_BOND_CB_LIST", "columns": "ALL",
              "pageSize": "500", "pageNumber": "1", "source": "WEB", "client": "WEB",
              "filter": '(SECURITY_CODE in (%s))' % codes}
    j = requests.get(url, params=params, headers=UA, timeout=20).json()
    rows = ((j.get("result") or {}).get("data")) or []
    out = {}
    for row in rows:
        code = str(row.get("SECURITY_CODE", ""))
        def pick(*keys):
            for k in keys:
                v = row.get(k)
                if v is not None:
                    try: return float(v)
                    except (TypeError, ValueError): pass
            return None
        cv = pick("TRANSFER_VALUE", "CONV_VALUE", "TRANSFER_VALUE_NEW")
        pr = pick("CONV_PREMIUM_RATIO", "TRANSFER_PREMIUM_RATIO", "CONVERT_PREMIUM_RATIO", "PREMIUM_RATIO")
        if code and (cv is not None or pr is not None):
            out[code] = {"convValue": cv, "premium": pr}
    return out

def em_ann():
    out, seen = [], set()
    today = datetime.datetime.now(TZ).date()
    for bcode, bname, scode, sname in BONDS:
        try:
            j = requests.get("https://np-anotice-stock.eastmoney.com/api/security/ann",
                             params={"sr": "-1", "page_size": "50", "page_index": "1",
                                     "ann_type": "A", "client_source": "web",
                                     "stock_list": scode, "f_node": "0", "s_node": "0"},
                             headers=UA, timeout=15).json()
            items = (j.get("data") or {}).get("list") or []
            for it in items:
                title = (it.get("title") or "").strip()
                if not title or not ANN_KW.search(title): continue
                d = (it.get("notice_date") or it.get("showtime") or "")[:10]
                try: dt = datetime.date.fromisoformat(d)
                except ValueError: continue
                if (today - dt).days > ANN_DAYS: continue
                art = it.get("art_code") or ""
                key = art or title
                if key in seen: continue
                seen.add(key)
                out.append({"code": bcode, "bond": bname, "stock": sname,
                            "title": title, "date": d,
                            "url": "https://data.eastmoney.com/notices/detail/%s/%s.html" % (scode, art)})
        except Exception as e:
            print("ann fail %s: %s" % (scode, e))
        time.sleep(0.4)
    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:40]

def main():
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    quotes, src = {}, ""
    try:
        quotes = em_quotes(); src = "东方财富"
    except Exception as e:
        print("EM quotes fail: %s, fallback tencent" % e)
        try:
            quotes = tx_quotes(); src = "腾讯行情(仅转债)"
        except Exception as e2:
            print("TX quotes fail: %s" % e2)
    prem = {}
    try:
        prem = em_premium()
    except Exception as e:
        print("premium fail: %s" % e)
    try:
        ann = em_ann()
    except Exception as e:
        print("ann fail: %s" % e); ann = []

    cb = []
    for bcode, bname, scode, sname in BONDS:
        row = {"code": bcode}
        q = quotes.get(bcode)
        if q: row["price"], row["chg"] = q["p"], q["chg"]
        sq = quotes.get(scode)
        if sq: row["stockChg"] = sq["chg"]
        p = prem.get(bcode) or {}
        if p.get("convValue") is not None: row["convValue"] = p["convValue"]
        if p.get("premium") is not None:   row["premium"] = p["premium"]
        cb.append(row)

    # event_base：若抓到公告，取最新公告日期中较早者之后的基准意义有限，保持原基准即可
    data = {"generated": now, "quote_src": src, "cb": cb, "ann": ann,
            "event_base": "2026-11-27"}
    json.dump(data, io.open("data.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("OK src=%s quotes=%d/26 premium=%d ann=%d" % (src, len(quotes), len(prem), len(ann)))

if __name__ == "__main__":
    main()
