#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 Wayback 恢复 bbs.deeptimes.net 全部已存档帖子(所有版块)的原始HTML。
断点续传、限速友好。产物给 build_site.py 生成站点用。
用法：python3 recover_all.py
"""
import subprocess, re, os, time
from collections import defaultdict

RAW="/home/fabric/bbs/deeptimes-archive/_src/raw"
os.makedirs(RAW, exist_ok=True)

def curl(url, timeout=90):
    cmd=["curl","-sL","--compressed","--max-time",str(timeout),
         "--retry","6","--retry-delay","5","--retry-all-errors","--retry-max-time","200", url]
    try: return subprocess.run(cmd,capture_output=True).stdout
    except Exception: return b""

# tid -> {page: (ts,url)}  取每页最新快照
snaps=defaultdict(dict)
for line in open("/home/fabric/bbs/wb_forum.txt",errors="replace").read().splitlines():
    p=line.split()
    if len(p)<2: continue
    url,ts=p[0],p[1]
    if "mod=viewthread" not in url: continue
    mt=re.search(r"tid=(\d+)",url)
    if not mt: continue
    pg=re.search(r"[?&]page=(\d+)",url); pg=pg.group(1) if pg else "1"
    cur=snaps[mt.group(1)].get(pg)
    if not cur or ts>cur[0]: snaps[mt.group(1)][pg]=(ts,url)

existing=set(os.listdir(RAW))
def have(tid,pg): return any(x.startswith(f"{tid}_{pg}__wb") for x in existing)

total=sum(len(v) for v in snaps.values())
print(f"待恢复 {len(snaps)} 个帖子 / {total} 个页面。已存 {len(existing)} 个文件。")
done=0; got=0
for tid in snaps:
    for pg,(ts,url) in sorted(snaps[tid].items()):
        done+=1
        if have(tid,pg): continue
        b=curl(f"http://web.archive.org/web/{ts}id_/{url}")
        if len(b)<2000:
            time.sleep(3); continue
        fn=f"{RAW}/{tid}_{pg}__wb{ts}.html"
        open(fn,"wb").write(b); existing.add(os.path.basename(fn)); got+=1
        if got%25==0: print(f"  进度 {done}/{total} | 新下载 {got}")
        time.sleep(1.6)
print(f"完成：新下载 {got} 个页面，raw 目录共 {len(os.listdir(RAW))} 个文件。")
