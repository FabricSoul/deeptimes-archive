# 深度时空 太空游戏攻略存档 · DeepTimes Space Game Archive

已关站的中文太空游戏社区 **深度时空（bbs.deeptimes.net）** 的社区保存性存档。
内容来自 [Wayback Machine](https://web.archive.org/web/*/bbs.deeptimes.net) 的公开存档，涵盖
**X3：地球人冲突 / 阿尔比恩序曲 / 法纳姆遗产**、**X4：基石**、**自由枪骑兵 Freelancer**、
**群星 Stellaris**、**太空引擎 Space Engine** 等太空模拟 / 太空游戏的攻略、任务流程、汉化与心得。

🌐 站点： https://fabricsoul.github.io/deeptimes-archive/

## 关于版权 / About

- 所有帖子的**版权归各原作者所有**，页面中保留了原作者署名与发帖时间。
- 本站为**非官方保存性镜像**，仅供游戏玩家学习交流与资料保存，不含任何商业用途。
- 如果您是原作者或原站长，希望某内容下架、修改或补充署名，请提交
  [GitHub Issue](https://github.com/FabricSoul/deeptimes-archive/issues)，我们会尽快处理。
- Content © original authors. This is an unofficial preservation mirror of the defunct
  forum bbs.deeptimes.net. Takedown requests welcome via Issues.

## 如何重建 / Rebuild

```bash
python3 tools/recover_all.py   # 从 Wayback 恢复原始 HTML 到 _src/raw/（断点续传）
python3 tools/build_site.py    # 由 _src/raw/ 生成本静态站点
```

`_src/`（原始 HTML 与日志）不纳入版本库，可随时由上面脚本重建。
