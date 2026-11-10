# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 风格，版本号遵循[语义化版本](https://semver.org/lang/zh-CN/)。

本 skill 与原 skill 的关系：**同一思路、同一 6 件交付契约，唯一核心升级是天气图的三级阶梯**；其余部分保持与原 skill 一致。

## 1.0.0 - 2026-11-09

### Added
- **天气图三级阶梯（核心升级）**，对应原 skill "目的地在唯一可用的大区域图上读不清" 的空白：
  - `SKILL.md` 非协商项新增第 7 条：不放大糊图、不猜色，走阶梯并保留出处链。
  - `SKILL.md` Step 6 新增 *Chart legibility* 段：① 官方图原样 → ② 小区域节选 → ③ 定位底 + 官方采样填色；verdict 逐像素采样方式不变，只换底图。
  - `references/weather.md` 新增 *Legibility ladder* 一节（46 行纯增量）：三级适用条件与出处要求、第 3 级实操（矢量定位底 + 官方图例色值填充 + 横幅/`_note` 出处链）、两条禁止事项；failure modes 补 2 行。
  - 首次检查"目的地附近是否存在小区域图"并记录产品存在与否——缺失本身是要报告的事实。
- **适用范围显性化（对齐原 skill 思路）**：frontmatter 与开篇改为"全球任何地方、自驾/自由行/铁路/渡轮/包车/混合出行方式"，不把 skill 限定成自驾专用；其余工作流、契约、脚本与原 skill 相同。

### Fixed
- `scripts/build_maps.py` 图例文字 x 坐标未乘投影横轴比例（`KX`），导致图例文字与色块错位；补 `tx_proj = tx * g.KX`（制图缺陷修复，不改变 skill 范围）。

## 0.1.0 - 2026-11-09

### Added
- 基线：`Travel Docs` skill 原版。
  - 6 件交付物契约（2 PNG + 1 PDF + 3 XLSX，固定文件名与工作表结构）。
  - 6 条非协商项：geocode 核坐标、OSRM 算里程、检索价格、先问体力、官方图采样出天气结论、司机件不带预算/个人信息。
  - 7 步工作流与 4 份 references（deliverables / maps / weather / example）。
  - 7 个脚本：`geocode.py`、`route.py`、`fetch_basemap.py`、`build_maps.py`、`mk_xlsx.py`、`build_weather_pdf.py`、`trip.example.json`。

> `docs/lessons-learned.md` 是案例复盘，其中仅天气阶梯与图例修复进入了 skill；日期整包重做、Windows 编码等为项目过程记录，不属 skill 范围。
