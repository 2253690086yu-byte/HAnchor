# -*- coding: utf-8 -*-
"""
export_for_harness.py — 把 HAnchor 基线技能导出为成熟 harness 可直接加载的格式

用法:
  python tools/export_for_harness.py --target skills --out export/skills          # Agent Skills 约定(Claude Code / ZCode 等)
  python tools/export_for_harness.py --target codex  --out export/codex-prompts   # Codex CLI ~/.codex/prompts/
  python tools/export_for_harness.py --target cursor --out export/cursor-rules    # Cursor .cursor/rules/
  python tools/export_for_harness.py --all          # 连服务绑定型技能一并导出(默认只导可移植型)

处理逻辑:
  1. 版本剪裁:每个插件只取最高版本(README 改进优先级③),消除多版本共存
  2. 技能去重:按技能名唯一化,多版本同名只留最新插件的那份
  3. 分类:零依赖标记 → portable;否则 → service-bound(默认跳过,--all 包含)
  4. frontmatter 规范化:name/description(合并多行续行,块标量防炸 YAML)/allowed-tools/version;
     其余私有字段剥离(--keep-extras 保留)
  5. 整目录拷贝技能载荷(SKILL.md + references/ + scripts/ + assets/)
  6. 产出 PORTABILITY.md 清单与 00-index.md 索引
"""
import os, re, shutil, argparse, collections

ROOT = os.environ.get("HANCHOR_ROOT") or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CACHE = os.path.join(ROOT, "plugins-cache")

RUNTIME_MARKS = {
    "MCP 工具": re.compile(r"mcp__[a-zA-Z0-9_]+"),
    "内部服务端点": re.compile(r"qyapi[.]|docs[.]qq[.]com|doc[.]weixin|lbs[.]qq[.]com|stockbuddy|gongyi[.]qq"),
    "本地二进制": re.compile(r"[.]exe|cli[.]cjs|prebuilds"),
    "HAnchor 运行时": re.compile(r"[.]hanchor/|hanchor-binaries|Haipc|haipc"),
}

def ver_key(vdir):
    """5.9.3-ha.<hash> → (5,9,3) 用于比较"""
    core = re.split(r"[-+]", vdir)[0]
    parts = []
    for x in core.split("."):
        try: parts.append(int(x))
        except ValueError: parts.append(0)
    return tuple(parts)

def latest_versions():
    """插件名 → 最新版本目录路径(基线缺失——如公开仓独立使用/合成根——返回空,只剩 additions 组)"""
    best = {}
    if not os.path.isdir(CACHE):
        return best
    for mp in sorted(os.listdir(CACHE)):
        mpdir = os.path.join(CACHE, mp)
        if not os.path.isdir(mpdir): continue
        for pl in os.listdir(mpdir):
            pldir = os.path.join(mpdir, pl)
            if not os.path.isdir(pldir): continue
            for v in os.listdir(pldir):
                vdir = os.path.join(pldir, v)
                if not os.path.isdir(vdir): continue
                cur = best.get(pl)
                if cur is None or ver_key(v) > ver_key(os.path.basename(cur)):
                    best[pl] = vdir
    return best

def parse_frontmatter(text):
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n?(.*)", text, re.S)
    if not m: return {}, text
    head, body = m.group(1), m.group(2)
    fields, order, cur = {}, [], None
    for line in head.splitlines():
        km = re.match(r"^([A-Za-z0-9_-]+):(.*)$", line)
        if km:
            cur = km.group(1)
            if cur not in fields: order.append(cur)
            v = km.group(2).strip()
            # 原始块标量指示符(>、|- 等)不是值本身
            fields[cur] = "" if v in (">", ">-", "|", "|-", ">+", "|+") else v
        elif cur and line.strip():
            fields[cur] = (fields[cur] + " " if fields[cur] else "") + line.strip()
    return fields, body

def normalize_fm(fields, keep_extras):
    name = fields.get("name", "").strip()
    desc = fields.get("description", "").strip()
    keep = {"name": name, "description": desc}
    for k in ("allowed-tools", "version", "disable-model-invocation"):
        if fields.get(k, "").strip(): keep[k] = fields[k].strip()
    if keep_extras:
        for k, v in fields.items():
            if k not in keep and v and k not in ("metadata",): keep[k] = v
    return keep

def emit_fm(fm):
    out = ["---"]
    for k, v in fm.items():
        if k == "description" or (len(v) > 60) or (":" in v and not v.startswith('"')):
            out.append(f'{k}: >-')
            for seg in wrap(v, 100): out.append(f"  {seg}")
        else:
            out.append(f"{k}: {v}")
    out.append("---")
    return "\n".join(out) + "\n"

def wrap(s, w):
    s = re.sub(r"\s+", " ", s.replace("\r", " ").replace("\n", " ")).strip()
    lines, cur = [], ""
    for tok in s.split(" "):
        if cur and len(cur) + 1 + len(tok) > w:
            lines.append(cur); cur = tok
        else:
            cur = f"{cur} {tok}" if cur else tok
    if cur: lines.append(cur)
    return lines or [""]

def classify(skill_md_text):
    hits = [label for label, rx in RUNTIME_MARKS.items() if rx.search(skill_md_text)]
    return hits

def collect():
    """三遍采集:先 skills/<名>/ 布局,再根布局(SKILL.md 直接在版本目录),最后 additions 自有组
    ——同名时基线优先(plugins-cache 权威,additions 不遮蔽基线)"""
    latest = sorted(latest_versions().items())
    skills = {}
    for pl, vdir in latest:
        sdir = os.path.join(vdir, "skills")
        if not os.path.isdir(sdir): continue
        for s in sorted(os.listdir(sdir)):
            if os.path.isfile(os.path.join(sdir, s, "SKILL.md")):
                skills[s] = (pl, os.path.join(sdir, s))
    for pl, vdir in latest:
        p = os.path.join(vdir, "SKILL.md")
        if os.path.isfile(p):
            fm, _ = parse_frontmatter(open(p, "rb").read().decode("utf-8", "replace"))
            name = (fm.get("name") or "").strip() or pl.removeprefix("skill-")
            if name and name not in skills:
                skills[name] = (pl, vdir)
    additions = os.path.join(ROOT, "additions")
    if os.path.isdir(additions):
        for grp in sorted(os.listdir(additions)):
            gdir = os.path.join(additions, grp, "skills")
            if not os.path.isdir(gdir): continue
            for s in sorted(os.listdir(gdir)):
                if os.path.isfile(os.path.join(gdir, s, "SKILL.md")):
                    skills.setdefault(s, (f"additions:{grp}", os.path.join(gdir, s)))
    return skills

def export(target, outdir, include_service_bound, keep_extras, prefix=""):
    skills = collect()
    manifest, exported = [], []
    os.makedirs(outdir, exist_ok=True)
    for name, (pl, sd) in sorted(skills.items()):
        text = open(os.path.join(sd, "SKILL.md"), "rb").read().decode("utf-8", "replace")
        hits = classify(text)
        fm, body = parse_frontmatter(text)
        fm = normalize_fm(fm, keep_extras)
        out_name = prefix + name
        fm["name"] = out_name
        if hits and not include_service_bound:
            manifest.append((name, pl, "SKIP 服务绑定: " + ",".join(hits), fm["description"][:60]))
            continue
        if target == "skills":
            dst = os.path.join(outdir, out_name)
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(sd, dst, ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".DS_Store"))
            open(os.path.join(dst, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(emit_fm(fm) + body)
        else:
            ext = ".mdc" if target == "cursor" else ".md"
            open(os.path.join(outdir, out_name + ext), "w", encoding="utf-8", newline="\n").write(
                convert(target, out_name, fm, body, sd))
        exported.append(name)
        manifest.append((out_name, pl, ("OK" if not hits else "OK(服务绑定:" + ",".join(hits) + ")"), fm["description"][:60]))
    return manifest, exported, skills

def convert(target, name, fm, body, sd):
    """skills 之外的格式转换"""
    if target == "codex":
        refs = sorted(os.path.relpath(os.path.join(dp, f), sd)
                      for dp, _, fs in os.walk(sd) for f in fs
                      if not f.endswith("SKILL.md") and f.endswith((".md", ".py", ".js", ".sh", ".json")))
        reflist = "\n".join(f"- {r}" for r in refs[:40])
        return (f"# {name}\n\n> {fm['description'][:400]}\n"
                f"> 触发方式:在 Codex 中输入 `/{name}`;技能资料目录: `{sd}`\n"
                f"> 附属文件(按需 Read):\n{reflist}\n\n---\n\n{body}")
    if target == "cursor":
        return (f"---\ndescription: {fm['description'][:200]}\nglobs: \nalwaysApply: false\n---\n\n"
                f"# {name}\n\n技能资料目录: `{sd}`(附属 references/scripts 按需读取)\n\n{body}")
    raise ValueError(target)

def build_plugin(outdir, include_service_bound, keep_extras, prefix=""):
    """ZCode 本地插件形式:.zcode-plugin/plugin.json + skills/(可从本地市场安装,整体启停)"""
    skills = collect()
    pdir = os.path.join(outdir, "skills")
    os.makedirs(os.path.join(outdir, ".zcode-plugin"), exist_ok=True)
    os.makedirs(pdir, exist_ok=True)
    import json as _json
    open(os.path.join(outdir, ".zcode-plugin", "plugin.json"), "w", encoding="utf-8", newline="\n").write(_json.dumps({
        "name": "hanchor-skills", "version": "1.0.0",
        "description": "HAnchor 自有规范体系可移植技能集(版本剪裁+去品牌化,生成于 2026-11-05)",
        "skills": "skills",
    }, ensure_ascii=False, indent=2) + "\n")
    n = 0
    for name, (pl, sd) in sorted(skills.items()):
        text = open(os.path.join(sd, "SKILL.md"), "rb").read().decode("utf-8", "replace")
        if classify(text) and not include_service_bound: continue
        fm, body = parse_frontmatter(text)
        fm = normalize_fm(fm, keep_extras)
        out_name = prefix + name; fm["name"] = out_name
        dst = os.path.join(pdir, out_name)
        if os.path.exists(dst): shutil.rmtree(dst)
        shutil.copytree(sd, dst, ignore=shutil.ignore_patterns("node_modules", "__pycache__", ".DS_Store"))
        open(os.path.join(dst, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(emit_fm(fm) + body)
        n += 1
    print(f"构建 ZCode 插件: {n} 个技能 → {outdir}(.zcode-plugin/plugin.json + skills/)")
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", choices=["skills", "codex", "cursor", "zcode-plugin"], default="skills")
    ap.add_argument("--out", required=True)
    ap.add_argument("--all", action="store_true", help="包含服务绑定型技能")
    ap.add_argument("--keep-extras", action="store_true", help="保留私有 frontmatter 字段")
    ap.add_argument("--prefix", default="", help="技能名前缀(如 ha-,防与宿主已有技能撞名遮蔽)")
    a = ap.parse_args()
    outdir = a.out if os.path.isabs(a.out) else os.path.join(ROOT, a.out)
    if a.target == "zcode-plugin":
        build_plugin(outdir, a.all, a.keep_extras, a.prefix); return
    manifest, exported, all_skills = export(a.target, outdir, a.all, a.keep_extras, a.prefix)

    with open(os.path.join(outdir, "PORTABILITY.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 导出清单\n\n> 来源: plugins-cache(版本剪裁后)+ additions(自有组,标 additions:) | 目标格式: %s | 服务绑定%s导出\n\n"
                "| 技能 | 来源插件 | 状态 | 描述 |\n|---|---|---|---|\n" % (a.target, "已" if a.all else "未"))
        for n, pl, st, d in manifest:
            f.write(f"| {n} | {pl} | {st} | {d} |\n")
    with open(os.path.join(outdir, "00-index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("# 技能索引(%d 项)\n\n" % len(exported))
        for n, pl, st, d in manifest:
            if st.startswith("OK"): f.write(f"- **{n}**({pl})— {d}\n")
    skip = len(all_skills) - len(exported)
    print(f"导出 {len(exported)} 个技能 → {outdir}(跳过服务绑定 {skip})")
    print(f"体积: {sum(os.path.getsize(os.path.join(outdir, f)) for f in os.listdir(outdir) if os.path.isfile(os.path.join(outdir, f)))//1024}KB(顶层)")

if __name__ == "__main__":
    main()
