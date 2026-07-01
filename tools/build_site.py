#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 _src/raw 里恢复的 Discuz 原始HTML 生成为一个 SEO 友好的静态存档站点。
可反复运行(幂等)，随时根据当前已恢复的内容重新生成。
用法：python3 build_site.py
"""
import os, re, html, json, hashlib
from collections import defaultdict, OrderedDict

ROOT   = "/home/fabric/bbs/deeptimes-archive"
RAW    = f"{ROOT}/_src/raw"
SITE_BASE = "https://fabricsoul.github.io/deeptimes-archive"
SITE_NAME = "深度时空太空游戏攻略存档"
SITE_NAME_EN = "DeepTimes Space Game Archive"
NOINDEX_MIN_CHARS = 300   # 正文少于此值 → noindex，避免薄内容拖累SEO

# 版块中文名 -> (英文slug, 展示名 CN+EN)
SECTIONS = {
 "X3: 地球人冲突(TC)/阿尔比恩序曲(AP)讨论": ("x3-terran-conflict-albion-prelude","X3：地球人冲突 / 阿尔比恩序曲（X3: Terran Conflict / Albion Prelude / Farnham's Legacy）"),
 "X4: 基石(X4: Foundations)": ("x4-foundations","X4：基石（X4: Foundations）"),
 "X: 重生(X: Rebirth)": ("x-rebirth","X：重生（X: Rebirth）"),
 "太空工程师(Space Engineers)": ("space-engineers","太空工程师（Space Engineers）"),
 "太空引擎(Space Engine)": ("space-engine","太空引擎（Space Engine）"),
 "群星(Stellaris)": ("stellaris","群星（Stellaris）"),
 "遥远的世界:宇宙(Distant Worlds:Universe)": ("distant-worlds-universe","遥远的世界：宇宙（Distant Worlds: Universe）"),
 "暗星一号(Darkstar One)": ("darkstar-one","暗星一号（Darkstar One）"),
 "星际之狼/3(Star Wolves)": ("star-wolves","星际之狼 3（Star Wolves）"),
 "自由枪骑兵 Freelancer Online": ("freelancer","自由枪骑兵（Freelancer）"),
 "自由枪骑兵(FreeLancer)区": ("freelancer","自由枪骑兵（Freelancer）"),
 "太空游戏综合区": ("space-games-general","太空游戏综合区（Space Games General）"),
 "其他科幻游戏综合区": ("other-scifi-games","其他科幻游戏综合区（Other Sci-Fi Games）"),
 "太空/科幻游戏 前沿科学 新闻发布": ("space-scifi-news","太空/科幻游戏 · 前沿科学新闻（News）"),
 "综合讨论区": ("general-discussion","综合讨论区（General Discussion）"),
 "X3: 地球人模组脚本区(TC/AP MOD&Scripts)": ("x3-tc-ap-mods","X3：地球人冲突/阿尔比恩序曲 模组脚本（TC/AP MOD & Scripts）"),
 "X3: 重聚模组脚本区(Reunion MOD&Scripts)": ("x3-reunion-mods","X3：重聚 模组脚本（Reunion MOD & Scripts）"),
 "X: 重生模组脚本(X: Rebirth MOD&Scripts)": ("x-rebirth-mods","X：重生 模组脚本（X: Rebirth MOD & Scripts）"),
 "深度时空官方游戏正版游戏店": ("official-store","深度时空官方正版游戏店（Official Store）"),
}
SKIP_SECTIONS = {"提示信息", "Discuz! Board", ""}  # Discuz 系统/错误页，非内容
def slugify(s):
    s=re.sub(r"[^A-Za-z0-9]+","-",s).strip("-").lower()
    return s or "x"
_seen_slug={}
def section_meta(name):
    if name in SECTIONS: return SECTIONS[name]
    m=re.search(r"[（(]([A-Za-z0-9 :/\-']{3,})[)）]",name) or re.search(r"([A-Za-z][A-Za-z0-9 :/\-']{2,})",name)
    base=slugify(m.group(1)) if m else ("sec-"+hashlib.md5(name.encode()).hexdigest()[:6])
    slug=base
    i=2
    while slug in _seen_slug and _seen_slug[slug]!=name:
        slug=f"{base}-{i}"; i+=1
    _seen_slug[slug]=name
    return (slug, name)

# ---------- 解析 raw ----------
def strip_tags(s):
    s=re.sub(r"(?is)<script.*?</script>|<style.*?</style>","",s)
    s=re.sub(r"(?is)<div class=\"quote\">.*?</div>","",s)  # 去引用块噪声(尽力)
    s=re.sub(r"(?i)<br\s*/?>","\n",s); s=re.sub(r"(?i)</(p|div|td|tr|li|h\d)>","\n",s)
    s=re.sub(r"(?s)<[^>]+>","",s); s=html.unescape(s)
    s=re.sub(r"[ \t]+"," ",s); s=re.sub(r"\n{3,}","\n\n",s)
    return s.strip()

def parse_file(path):
    raw=open(path,"rb").read().decode("utf-8","replace")
    mt=re.search(r"<title>(.*?)</title>",raw,re.S)
    if not mt: return None
    parts=[p.strip() for p in html.unescape(mt.group(1)).split(" - ") if p.strip()]
    # 结构固定为: 标题 - 版块 - 深度时空宇宙/太空游戏社区 - Powered by Discuz!
    # 版块永远是倒数第三段；标题可能自身含 " - "，故取前面全部
    if len(parts)>=3:
        section=parts[-3]; title=" - ".join(parts[:-3]) or parts[0]
    else:
        title=parts[0] if parts else ""; section="综合"
    posts=re.findall(r'id="postmessage_\d+"[^>]*>(.*?)</td>',raw,re.S)
    floors=[t for t in (strip_tags(p) for p in posts) if len(t)>4]
    # 作者/日期(尽力)
    author=None
    ma=re.search(r'class="xw1"[^>]*>([^<]{1,30})</a>',raw) or re.search(r"本帖最后由\s*(\S{1,30}?)\s*于",raw)
    if ma: author=ma.group(1).strip()
    md=re.search(r"发表于\s*(\d{4}-\d{1,2}-\d{1,2})",raw) or re.search(r"本帖最后由.{0,20}?于\s*(\d{4}-\d{1,2}-\d{1,2})",raw)
    date=md.group(1) if md else None
    return title, section, floors, author, date

# tid -> {page: parsed}
threads={}
for fn in os.listdir(RAW):
    if not fn.endswith(".html"): continue
    m=re.match(r"(\d+)_(\w+?)__wb(\d+)\.html",fn) or re.match(r"(\d+)_(\w+?)__cc(\d+)\.html",fn)
    if not m: continue
    tid,pg=m.group(1),m.group(2); ts=m.group(3)
    parsed=parse_file(os.path.join(RAW,fn))
    if not parsed: continue
    threads.setdefault(tid,{"pages":{},"ts":ts})
    threads[tid]["pages"][pg]=parsed
    if ts>threads[tid]["ts"]: threads[tid]["ts"]=ts

# 合并每帖多页
docs=[]   # dict per thread
for tid,d in threads.items():
    order=sorted(d["pages"], key=lambda x:(len(x),x))  # p1,p2,...,p10,p26
    title=section=None; floors=[]; author=None; date=None
    for pg in order:
        t,s,fl,a,dt=d["pages"][pg]
        title=title or t; section=section or s
        author=author or a; date=date or dt
        floors+=fl
    if not title or not floors: continue
    if (section or "").strip() in SKIP_SECTIONS: continue
    body_chars=sum(len(re.sub(r"\s","",f)) for f in floors)
    docs.append({"tid":tid,"title":title,"section":section or "综合","floors":floors,
                 "author":author,"date":date,"chars":body_chars,"ts":d["ts"]})

# 分组
by_sec=defaultdict(list)
for doc in docs:
    slug,disp=section_meta(doc["section"])
    doc["slug"],doc["disp"]=slug,disp
    by_sec[slug].append(doc)
for slug in by_sec: by_sec[slug].sort(key=lambda x:-x["chars"])
sec_order=sorted(by_sec, key=lambda s:-len(by_sec[s]))
sec_disp={by_sec[s][0]["slug"]:by_sec[s][0]["disp"] for s in by_sec}

print(f"帖子 {len(docs)} 篇 | 版块 {len(by_sec)} 个")

# ---------- HTML 组件 ----------
def esc(s): return html.escape(s,quote=True)
def excerpt(floors, n=150):
    t=floors[0] if floors else ""
    t=re.sub(r"^本帖最后由.{0,40}?编辑\s*","",t)
    t=re.sub(r"\s+"," ",t).strip()
    return t[:n]

def head(title, desc, canonical, rel_prefix, noindex=False, extra_ld=None):
    robots='<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="index,follow">'
    ld=""
    if extra_ld:
        for obj in extra_ld:
            ld+=f'<script type="application/ld+json">{json.dumps(obj,ensure_ascii=False)}</script>\n'
    return f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}"><meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary">
<link rel="stylesheet" href="{rel_prefix}assets/style.css">
{ld}</head><body>
<header class="site"><a href="{rel_prefix}index.html" class="brand">深度时空 · 太空游戏攻略存档</a>
<span class="tag">DeepTimes Space Game Archive</span><a class="gh" href="https://github.com/FabricSoul/deeptimes-archive" target="_blank" rel="noopener">GitHub ↗</a></header>'''

FOOTER=f'''<footer class="site">
<p><strong>关于本站</strong>：这是对已关站的太空游戏社区 <b>深度时空 bbs.deeptimes.net</b> 的非官方社区存档，
内容取自 <a href="https://web.archive.org/web/*/bbs.deeptimes.net" rel="nofollow">Wayback Machine</a> 公开存档，
<b>版权归各原作者所有</b>，帖内保留了原作者署名与发帖时间。仅供游戏玩家学习交流与资料保存之用。</p>
<p>如您是原作者或原站长，希望某内容下架或补充署名，请提交 GitHub Issue，我们会尽快处理。</p>
<p class="muted">Archive of the defunct Chinese space-game forum DeepTimes (bbs.deeptimes.net). Content © original authors. Preservation mirror.</p>
</footer></body></html>'''

def breadcrumb_ld(items):
    return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":n,"item":u} for i,(n,u) in enumerate(items)]}

os.makedirs(f"{ROOT}/t",exist_ok=True); os.makedirs(f"{ROOT}/s",exist_ok=True); os.makedirs(f"{ROOT}/assets",exist_ok=True)

# ---------- 帖子页 ----------
search_index=[]
sitemap=[]
for doc in docs:
    tid=doc["tid"]; url=f"{SITE_BASE}/t/{tid}.html"; rp="../"
    noindex = doc["chars"] < NOINDEX_MIN_CHARS
    desc=excerpt(doc["floors"])
    ptitle=f'{doc["title"]}｜{doc["disp"].split("（")[0]}攻略｜深度时空存档'
    dp={"@context":"https://schema.org","@type":"DiscussionForumPosting",
        "headline":doc["title"][:110],"articleBody":doc["floors"][0][:5000],
        "author":{"@type":"Person","name":doc["author"] or "深度时空社区用户"},
        "url":url,"inLanguage":"zh-CN","about":doc["disp"],
        "isPartOf":{"@type":"WebSite","name":SITE_NAME,"url":SITE_BASE+"/"},
        "commentCount":max(0,len(doc["floors"])-1)}
    if doc["date"]: dp["datePublished"]=doc["date"]
    bc=breadcrumb_ld([("首页",SITE_BASE+"/"),(doc["disp"].split("（")[0],f'{SITE_BASE}/s/{doc["slug"]}.html'),(doc["title"][:60],url)])
    parts=[head(ptitle,desc,url,rp,noindex,[dp,bc])]
    parts.append(f'''<nav class="crumb"><a href="{rp}index.html">首页</a> › <a href="{rp}s/{doc["slug"]}.html">{esc(doc["disp"].split("（")[0])}</a> › <span>{esc(doc["title"][:40])}</span></nav>''')
    meta_line=f'原作者：{esc(doc["author"])}　' if doc["author"] else ''
    meta_line+=f'发表：{doc["date"]}　' if doc["date"] else ''
    parts.append(f'''<article><h1>{esc(doc["title"])}</h1>
<p class="src">{meta_line}来源：bbs.deeptimes.net（已关站）· <a href="https://web.archive.org/web/{doc["ts"]}/https://bbs.deeptimes.net/forum.php?mod=viewthread&tid={tid}" rel="nofollow">Wayback 存档</a></p>''')
    for i,fl in enumerate(doc["floors"],1):
        body="\n".join(f"<p>{esc(b)}</p>" for b in re.split(r"\n\s*\n",fl) if b.strip())
        parts.append(f'<section class="floor"><span class="fl">#{i}</span>{body}</section>')
    # 相关帖
    rel=[d for d in by_sec[doc["slug"]] if d["tid"]!=tid][:8]
    if rel:
        parts.append('<aside class="related"><h2>同版块相关攻略</h2><ul>')
        for r in rel: parts.append(f'<li><a href="{rp}t/{r["tid"]}.html">{esc(r["title"])}</a></li>')
        parts.append('</ul></aside>')
    parts.append('</article>')
    parts.append(FOOTER)
    open(f"{ROOT}/t/{tid}.html","w",encoding="utf-8").write("\n".join(parts))
    search_index.append({"t":doc["title"],"s":doc["disp"].split("（")[0],"u":f"t/{tid}.html"})
    if not noindex: sitemap.append((url,doc["ts"]))

# ---------- 版块页 ----------
for slug in sec_order:
    ds=by_sec[slug]; disp=ds[0]["disp"]; url=f"{SITE_BASE}/s/{slug}.html"; rp="../"
    game=disp.split("（")[0]
    ptitle=f'{game}攻略大全（{len(ds)}篇）｜深度时空太空游戏存档'
    desc=f'{game} 攻略、教程、任务流程、心得合集，共 {len(ds)} 篇，源自深度时空 bbs.deeptimes.net 社区存档。'
    bc=breadcrumb_ld([("首页",SITE_BASE+"/"),(game,url)])
    p=[head(ptitle,desc,url,rp,False,[bc])]
    p.append(f'<nav class="crumb"><a href="{rp}index.html">首页</a> › <span>{esc(game)}</span></nav>')
    p.append(f'<h1>{esc(disp)}</h1><p class="lead">共 {len(ds)} 篇攻略／教程／心得，按内容体量排序。来自已关站的深度时空社区。</p><ul class="list">')
    for d in ds:
        p.append(f'<li><a href="{rp}t/{d["tid"]}.html">{esc(d["title"])}</a><span class="m">{len(d["floors"])}楼</span><p class="ex">{esc(excerpt(d["floors"],90))}</p></li>')
    p.append('</ul>'); p.append(FOOTER)
    open(f"{ROOT}/s/{slug}.html","w",encoding="utf-8").write("\n".join(p))
    sitemap.append((url,max(d["ts"] for d in ds)))

# ---------- 首页 ----------
url=SITE_BASE+"/"; rp=""
total=len(docs)
ptitle="深度时空 太空游戏攻略存档｜X3 X4 自由枪骑兵等中文攻略 | DeepTimes Archive"
desc=f"已关站的太空游戏社区『深度时空 bbs.deeptimes.net』攻略存档。X3(地球人冲突/阿尔比恩序曲)、X4基石、自由枪骑兵、群星、太空引擎等 {total} 篇中文攻略、任务流程与心得。"
wsld={"@context":"https://schema.org","@type":"WebSite","name":SITE_NAME,"alternateName":SITE_NAME_EN,
      "url":SITE_BASE+"/","inLanguage":"zh-CN","description":desc,
      "potentialAction":{"@type":"SearchAction","target":SITE_BASE+"/?q={search_term_string}","query-input":"required name=search_term_string"}}
p=[head(ptitle,desc,url,rp,False,[wsld])]
p.append(f'''<section class="hero"><h1>深度时空 · 太空游戏攻略存档</h1>
<p class="lead">这里保存着已关站的太空游戏社区 <b>深度时空（bbs.deeptimes.net）</b> 的攻略、任务流程、汉化与心得，
涵盖 <b>X3：地球人冲突/阿尔比恩序曲/法纳姆遗产</b>、<b>X4：基石</b>、<b>自由枪骑兵 Freelancer</b>、
<b>群星 Stellaris</b>、<b>太空引擎 Space Engine</b> 等太空模拟/太空游戏。共收录 <b>{total}</b> 篇。</p>
<input id="q" class="search" type="search" placeholder="搜索攻略标题，如：主线 / 赚钱 / 选船 / 建厂 …" autocomplete="off">
<ul id="results" class="list"></ul></section>''')
p.append('<h2>按游戏浏览</h2><div class="cards">')
for slug in sec_order:
    ds=by_sec[slug]; game=ds[0]["disp"].split("（")[0]
    top=ds[0]["title"]
    p.append(f'<a class="card" href="s/{slug}.html"><b>{esc(game)}</b><span>{len(ds)} 篇攻略</span><em>{esc(top[:28])}…</em></a>')
p.append('</div>')
p.append('<script src="assets/search.js"></script>')
p.append(FOOTER)
open(f"{ROOT}/index.html","w",encoding="utf-8").write("\n".join(p))

# ---------- 资产 / SEO 文件 ----------
open(f"{ROOT}/index.json","w",encoding="utf-8").write(json.dumps(search_index,ensure_ascii=False))

open(f"{ROOT}/assets/style.css","w",encoding="utf-8").write('''
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif;line-height:1.8;color:#1b1b1b;background:#faf9f6;margin:0}
a{color:#2155a4;text-decoration:none}a:hover{text-decoration:underline}
header.site{background:#111827;color:#fff;padding:14px 20px;display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
header.site .brand{color:#fff;font-weight:700;font-size:1.05em}
header.site .tag{color:#9aa4b2;font-size:.8em}
header.site .gh{margin-left:auto;color:#e2e8f0;font-size:.85em;border:1px solid #ffffff33;padding:3px 11px;border-radius:6px;white-space:nowrap}
header.site .gh:hover{background:#ffffff1a;text-decoration:none}
body>*:not(header):not(footer){max-width:900px;margin:0 auto;padding:0 18px}
h1{font-size:1.6em;border-bottom:3px solid #c0392b;padding-bottom:8px}
.crumb{color:#888;font-size:.85em;margin:16px 0}
.lead{color:#444}
.hero{background:#fff;border:1px solid #eee;border-radius:12px;padding:22px 24px;margin:22px auto}
.search{width:100%;padding:12px 14px;font-size:1em;border:2px solid #d5d5d5;border-radius:10px;margin-top:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin:14px auto;max-width:900px}
.card{background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:4px}
.card b{color:#c0392b}.card span{color:#888;font-size:.82em}.card em{color:#666;font-size:.82em;font-style:normal}
ul.list{list-style:none;padding:0}
ul.list li{background:#fff;border:1px solid #ececec;border-radius:8px;padding:10px 14px;margin:8px 0}
ul.list li .m{color:#aaa;font-size:.78em;margin-left:8px}
ul.list li .ex{color:#777;font-size:.85em;margin:4px 0 0}
article{background:#fff;border:1px solid #ececec;border-radius:12px;padding:6px 26px 20px;margin:18px auto}
article h1{color:#c0392b}
.src{color:#999;font-size:.82em;margin:-2px 0 14px}
.floor{border-top:1px dashed #eee;padding-top:6px;margin-top:14px}
.floor .fl{display:inline-block;background:#f0f0f0;color:#999;font-size:.74em;border-radius:4px;padding:1px 8px}
.related{margin-top:26px;border-top:2px solid #f0dada;padding-top:8px}
.related h2{font-size:1.05em}
footer.site{margin-top:40px;background:#f2efe9;border-top:1px solid #e2ddd2;color:#555;font-size:.85em;padding:20px}
footer.site{max-width:none}
footer.site p{max-width:900px;margin:8px auto}
.muted{color:#999}
@media(max-width:600px){.cards{grid-template-columns:1fr}}
''')

open(f"{ROOT}/assets/search.js","w",encoding="utf-8").write('''
fetch("index.json").then(r=>r.json()).then(idx=>{
 const q=document.getElementById("q"),res=document.getElementById("results");
 function render(list){res.innerHTML=list.slice(0,40).map(i=>
   `<li><a href="${i.u}">${i.t}</a><span class="m">${i.s}</span></li>`).join("");}
 q.addEventListener("input",()=>{const v=q.value.trim().toLowerCase();
   if(!v){res.innerHTML="";return;}
   render(idx.filter(i=>(i.t+" "+i.s).toLowerCase().includes(v)));});
 const p=new URLSearchParams(location.search).get("q");if(p){q.value=p;q.dispatchEvent(new Event("input"));}
});
''')

# robots.txt
open(f"{ROOT}/robots.txt","w").write(f'''User-agent: *
Allow: /

# AI / GEO crawlers explicitly welcome
User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Google-Extended
Allow: /

Sitemap: {SITE_BASE}/sitemap.xml
''')

# sitemap.xml
sm=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sm.append(f'<url><loc>{SITE_BASE}/</loc></url>')
for u,ts in sitemap:
    lm=f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts)>=8 else ""
    sm.append(f'<url><loc>{u}</loc>'+(f'<lastmod>{lm}</lastmod>' if lm else '')+'</url>')
sm.append('</urlset>')
open(f"{ROOT}/sitemap.xml","w").write("\n".join(sm))

# llms.txt (GEO)
ll=[f"# {SITE_NAME} ({SITE_NAME_EN})","",
    f"> 已关站的中文太空游戏社区『深度时空 bbs.deeptimes.net』的攻略存档。共 {len(docs)} 篇，涵盖 X3/X4/自由枪骑兵/群星/太空引擎等。内容版权归原作者，为社区保存性镜像。","",
    "## 按游戏分区"]
for slug in sec_order:
    ds=by_sec[slug]; game=ds[0]["disp"]
    ll.append(f"- [{game}]({SITE_BASE}/s/{slug}.html) — {len(ds)} 篇")
ll.append("\n## 代表性攻略")
for d in sorted(docs,key=lambda x:-x["chars"])[:20]:
    ll.append(f"- [{d['title']}]({SITE_BASE}/t/{d['tid']}.html)")
open(f"{ROOT}/llms.txt","w",encoding="utf-8").write("\n".join(ll))

open(f"{ROOT}/.nojekyll","w").write("")
open(f"{ROOT}/404.html","w",encoding="utf-8").write(head("页面未找到｜深度时空存档","404","/",  "")+ '<h1>页面未找到</h1><p><a href="/deeptimes-archive/">返回首页</a></p>'+FOOTER)

print(f"生成完成：{len(docs)} 帖 / {len(by_sec)} 版块 / sitemap 条目 {len(sitemap)+1}")
print("版块分布(slug : 数量 [原始中文版块名]):")
for slug in sec_order: print(f"  {slug}: {len(by_sec[slug])}  [{by_sec[slug][0]['section']}]")
