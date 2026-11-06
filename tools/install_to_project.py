# -*- coding: utf-8 -*-
"""
install_to_project.py — 把 HAnchor 技能能力一键装进某个项目(不碰 harness 全局,可随时干净卸载)

用法:
  安装   python tools/install_to_project.py <目标项目路径> [--harness zcode,claude,cursor,codex]
                                              [--all|--only a,b,c|--group doc,design] [--raw] [--no-rules] [--no-prefix]
  卸载   python tools/install_to_project.py <目标项目路径> --uninstall
  查看   python tools/install_to_project.py <目标项目路径> --status
  列表   python tools/install_to_project.py --list     # 全部可装技能+描述+分组(△=服务绑定,默认跳过)

保证:
  1. 只写目标项目的目录(.zcode/.claude/.cursor/.codex + AGENTS.md),绝不碰 ~/.zcode 等全局位置
  2. 技能载荷(references/scripts/assets/字体)逐字节拷贝 = 无损;
     SKILL.md frontmatter 默认规范化(多行描述修复,私有字段剥离)——--raw 可选原样
  3. 默认 ha- 前缀:工作区技能不会遮蔽宿主原生/插件技能(ZCode 优先级 user>workspace>plugin)
  4. 安装写入 <项目>/.zcode/hanchor-install.json 清单;--uninstall 按清单精确清除,AGENTS.md
     只摘掉带标记的块,文件若为本工具创建则一并删除 = 零残留
"""
import os, sys, json, shutil, argparse, datetime

if hasattr(sys.stdout, "reconfigure"):  # 输出符号已选 GBK 安全集(√△·—×→);errors 兜底防个别终端仍崩
    sys.stdout.reconfigure(errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_for_harness import collect, parse_frontmatter, normalize_fm, emit_fm, classify

ROOT = os.environ.get("HANCHOR_ROOT") or os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
RULES_SRC = os.path.join(ROOT, "additions", "01-user-rules", "meta-rules.md")
MANIFEST_NAME = "hanchor-install.json"
BEGIN, END = "<!-- hanchor:begin -->", "<!-- hanchor:end -->"

HARNESS = {
    # name -> (目录, 形式)  形式: skills=目录+SKILL.md / codex=扁平.md / cursor=扁平.mdc
    "zcode":  (os.path.join(".zcode", "skills"), "skills"),
    "claude": (os.path.join(".claude", "skills"), "skills"),
    "codex":  (os.path.join(".codex", "prompts"), "codex"),
    "cursor": (os.path.join(".cursor", "rules"), "cursor"),
}

GROUPS = {
    # 分组键 -> (中文名, 技能名列表)。公开仓只登记自有分组;基线分组属厂商内容不入公开仓,
    # 配置 HANCHOR_ROOT 后仍可 --only 装任意基线技能(名字用 --list 查,组标记显示 —)
    "writing":  ("文档三件套", "technical-writing documentation doc-coauthoring".split()),
}

def expand_groups(group_arg):
    """'doc,design' → 名字集合;未知分组键直接报错并列出可选键"""
    keys = [g.strip() for g in group_arg.split(",") if g.strip()]
    bad = [k for k in keys if k not in GROUPS]
    if bad:
        sys.exit("未知分组: " + ",".join(bad) + "\n可选: " + ", ".join(f"{k}({v[0]},{len(v[1])})" for k, v in GROUPS.items()))
    return {n for k in keys for n in GROUPS[k][1]}

def skill_text(sd):
    return open(os.path.join(sd, "SKILL.md"), "rb").read().decode("utf-8", "replace")

def payload(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(
        "node_modules", "__pycache__", ".DS_Store", ".*-plugin"))

def as_prompt(target, name, fm, body, sd):
    refs = sorted(os.path.relpath(os.path.join(dp, f), sd)
                  for dp, _, fs in os.walk(sd) for f in fs
                  if not f.endswith("SKILL.md") and f.endswith((".md", ".py", ".js", ".sh", ".json")))
    reflist = "\n".join(f"- {r}" for r in refs[:60])
    if target == "codex":
        return (f"# {name}\n\n> {fm['description'][:400]}\n> 资料目录: `{sd}`(附属文件按需 Read)\n"
                f"{reflist}\n\n---\n\n{body}")
    return (f"---\ndescription: {fm['description'][:200]}\nglobs: \nalwaysApply: false\n---\n\n"
            f"# {name}\n\n资料目录: `{sd}`\n\n{body}")

def list_skills():
    """全部可装技能 + 描述(--only 挑名字用;△=服务绑定型,默认跳过)"""
    skills = collect()
    rows = []
    for name, (pl, sd) in sorted(skills.items()):
        text = skill_text(sd)
        fm, _ = parse_frontmatter(text)
        rows.append((name, bool(classify(text)), " ".join(fm.get("description", "").split()).strip("'\"")))
    svc = sum(1 for _, s, _ in rows if s)
    print(f"可安装技能共 {len(rows)}(默认装可移植 {len(rows) - svc};△={svc} 个服务绑定,需 --all)")
    print("分组 --group: " + ", ".join(f"{k}={v[0]}({len(v[1])})" for k, v in GROUPS.items()) + "\n")
    in_group = {n: k for k, (_, ns) in GROUPS.items() for n in ns}
    w = max(len(n) for n, _, _ in rows)
    for name, s, desc in rows:
        g = in_group.get(name, "—")
        print(f"  {'△' if s else '·'} [{g:<7}] {name.ljust(w)}  {'— ' + desc[:80] + ('…' if len(desc) > 80 else '')}")

def install(project, harnesses, include_all, only, prefix, raw, with_rules):
    skills = collect()
    picked, skipped = [], []
    for name, (pl, sd) in sorted(skills.items()):
        if only and name not in only: continue
        hits = classify(skill_text(sd))
        if hits and not include_all:
            skipped.append((name, ",".join(hits))); continue
        picked.append((name, pl, sd))

    # 旧清单先读:重复安装不同技能集时,上一次装的目录也要留在清单里,否则卸载漏删
    mpath = os.path.join(project, ".zcode", MANIFEST_NAME)
    old = json.loads(open(mpath, encoding="utf-8").read()) if os.path.isfile(mpath) else {}

    manifest = {"installed_at": datetime.date.today().isoformat(),
                "source": "HAnchor plugins-cache(版本剪裁+去品牌化)",
                "prefix": prefix, "raw": raw,
                "agents_existed": old.get("agents_existed", os.path.isfile(os.path.join(project, "AGENTS.md"))),
                "harnesses": {}}
    count = 0
    for h in harnesses:
        rel, form = HARNESS[h]
        base = os.path.join(project, rel)
        os.makedirs(base, exist_ok=True)
        entries = []
        for name, pl, sd in picked:
            out_name = prefix + name
            text = skill_text(sd)
            fm, body = parse_frontmatter(text)
            fm = normalize_fm(fm, keep_extras=raw)  # raw 模式保留私有字段(仍做块标量修复)
            fm["name"] = out_name
            if form == "skills":
                dst = os.path.join(base, out_name)
                if os.path.exists(dst): shutil.rmtree(dst)
                payload(sd, dst)
                sk = "\n".join(text.splitlines()) if raw else emit_fm(fm) + body
                open(os.path.join(dst, "SKILL.md"), "w", encoding="utf-8", newline="\n").write(sk)
            else:
                f = os.path.join(base, out_name + (".mdc" if form == "cursor" else ".md"))
                open(f, "w", encoding="utf-8", newline="\n").write(as_prompt(form, out_name, fm, body, sd))
            entries.append(out_name)
            count += 1
        manifest["harnesses"][h] = {"dir": rel.replace("\\", "/"), "skills": entries}
    for h, v in old.get("harnesses", {}).items():  # 合并旧清单(本次没装到的 harness 整份保留)
        if h in manifest["harnesses"]:
            manifest["harnesses"][h]["skills"] = sorted(set(manifest["harnesses"][h]["skills"]) | set(v.get("skills", [])))
        else:
            manifest["harnesses"][h] = v

    rules_added = bool(old.get("rules_added"))  # 旧清单写过规则就保持 True,卸载时才能摘块
    if with_rules and os.path.isfile(RULES_SRC):
        am = os.path.join(project, "AGENTS.md")
        cur = open(am, encoding="utf-8").read() if os.path.isfile(am) else ""
        if BEGIN not in cur:
            rules = open(RULES_SRC, encoding="utf-8").read().strip()
            with open(am, "a", encoding="utf-8", newline="\n") as f:
                f.write(("\n" if cur.strip() else "") + f"{BEGIN}\n\n## HAnchor 用户级元规则(UR-xx)\n\n{rules}\n\n{END}\n")
            rules_added = True
    manifest["rules_added"] = rules_added

    os.makedirs(os.path.dirname(mpath), exist_ok=True)
    open(mpath, "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"√ 安装 {len(picked)} 个技能 × {len(harnesses)} 个 harness → {project}")
    for h, v in manifest["harnesses"].items(): print(f"   {h}: {v['dir']}/({len(v['skills'])} 项)")
    if rules_added: print("   AGENTS.md: 追加 UR-xx 元规则块(带 hanchor 标记)")
    if skipped:
        print(f"   跳过服务绑定 {len(skipped)} 个(--all 可包含): " + ", ".join(n for n, _ in skipped[:8]) + ("…" if len(skipped) > 8 else ""))
    print(f"卸载: python tools/install_to_project.py \"{project}\" --uninstall")

def prune_empty(path, stop):
    """空目录逐级向上清到 stop(不含);目录里有用户文件即停,绝不越界删项目根"""
    while path and path != stop and os.path.isdir(path) and not os.listdir(path):
        os.rmdir(path); path = os.path.dirname(path)

def uninstall(project):
    mpath = os.path.join(project, ".zcode", MANIFEST_NAME)
    if not os.path.isfile(mpath):
        print("未找到安装清单,无需卸载"); return
    m = json.loads(open(mpath, encoding="utf-8").read())
    removed, missing = 0, []
    for h, v in m.get("harnesses", {}).items():
        base = os.path.join(project, v["dir"])
        for name in v.get("skills", []):
            cands = [os.path.join(base, name), os.path.join(base, name + ".md"), os.path.join(base, name + ".mdc")]
            hit = next((c for c in cands if os.path.exists(c)), None)
            if hit: shutil.rmtree(hit) if os.path.isdir(hit) else os.remove(hit); removed += 1
            else: missing.append(name)
        prune_empty(base, project)  # 连 .claude/.codex 等顶层空壳一起清
    am = os.path.join(project, "AGENTS.md")
    if m.get("rules_added") and os.path.isfile(am):
        t = open(am, encoding="utf-8").read()
        if BEGIN in t and END in t:
            pre, rest = t.split(BEGIN, 1)
            _, post = rest.split(END, 1)
            new = pre.rstrip("\n") + ("\n" if post.strip() else "") + post.lstrip("\n")
            if not new.strip() and not m.get("agents_existed"): os.remove(am)
            else: open(am, "w", encoding="utf-8", newline="\n").write(new)
    os.remove(mpath)
    prune_empty(os.path.join(project, ".zcode"), project)
    print(f"√ 卸载完成: 移除 {removed} 项" + (f",未找到 {len(missing)} 项: {missing[:5]}" if missing else "") + " —— 零残留")

def status(project):
    mpath = os.path.join(project, ".zcode", MANIFEST_NAME)
    if not os.path.isfile(mpath):
        print("该项目未安装 HAnchor 能力"); return
    m = json.loads(open(mpath, encoding="utf-8").read())
    print(json.dumps(m, ensure_ascii=False, indent=2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?", help="目标项目路径(--list 时可省)")
    ap.add_argument("--harness", default="zcode", help="逗号分隔: zcode,claude,cursor,codex")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", default="", help="逗号分隔的技能名白名单(名字见 --list)")
    ap.add_argument("--group", default="", help="逗号分隔的分组键,见 --list(与 --only 取并集)")
    ap.add_argument("--list", action="store_true", help="列出全部可安装技能与描述")
    ap.add_argument("--no-prefix", action="store_true")
    ap.add_argument("--raw", action="store_true", help="SKILL.md 原样(保留私有 frontmatter 字段)")
    ap.add_argument("--no-rules", action="store_true", help="不往 AGENTS.md 写 UR-xx")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.list: list_skills(); return
    if not a.project: sys.exit("缺少目标项目路径;或用 --list 查看可安装技能清单")
    project = os.path.abspath(a.project)
    if not os.path.isdir(project):
        sys.exit(f"项目目录不存在: {project}")
    if a.uninstall: uninstall(project); return
    if a.status: status(project); return
    harnesses = [h.strip() for h in a.harness.split(",") if h.strip() in HARNESS]
    if not harnesses: sys.exit(f"无效 harness,可选: {', '.join(HARNESS)}")
    only = {x.strip() for x in a.only.split(",")} if a.only else None
    if a.group:
        gnames = expand_groups(a.group)
        only = gnames if only is None else only | gnames  # --group 与 --only 取并集
    install(project, harnesses, a.all, only, "" if a.no_prefix else "ha-", a.raw, not a.no_rules)

if __name__ == "__main__":
    main()
