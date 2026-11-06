# -*- coding: utf-8 -*-
"""
install_doc_skills.py — 文档三技能(technical-writing / documentation / doc-coauthoring)一条命令装齐

解决什么:公开仓按"只发自有内容"口径只带自写的 documentation,另两个技能在上游仓库。
本脚本把三个来源合并成一次安装:本仓已有的直接用,没有的按登记的 commit 锚点从上游
拉取并校验 SHA-256,再统一委托 install_to_project.py 安装(同样 ha- 前缀 + 清单化零残留)。

用法:
  安装   python tools/install_doc_skills.py <目标项目路径> [--harness zcode,claude,cursor,codex] [--no-rules]
  卸载   python tools/install_to_project.py <目标项目路径> --uninstall   (清单共享,卸载不变)

要求:git(拉上游用)+ 网络;本仓与上游均无需预下载。
"""
import os, sys, shutil, hashlib, subprocess, tempfile, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP_DIR = os.path.normpath(os.path.join(HERE, "..", "additions", "08-doc-skills"))
SKILLS = ("technical-writing", "documentation", "doc-coauthoring")

# 上游登记:技能 → (仓库, commit 锚点, 仓库内技能子路径, SKILL.md 的 SHA-256)
# 本仓已存在同名技能时优先用本地,不访问上游
UPSTREAM = {
    "technical-writing": ("https://github.com/luoling8192/technical-writing.git",
                          "5f684e950319bee8f773c3b5f5265c8bdda2900a", ".",
                          "d7a9cdf9beb34559aaa151a317b549b808b436042c51f7ecca55a557aefcdeab"),
    "doc-coauthoring": ("https://github.com/anthropics/skills.git",
                        "ca45fc496a3436251f191354091d557da31c15b5", "skills/doc-coauthoring",
                        "acb9b89b228fb818ffe2f464e40b1cdbf6948b50ceeeb7378f0e5b9d78c996ad"),
}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def fetch(name, workdir):
    """按 commit 锚点拉取上游技能目录 → workdir/<name>/,校验 SKILL.md 哈希"""
    url, commit, sub, want = UPSTREAM[name]
    clone = os.path.join(workdir, "clone-" + name)
    r = subprocess.run(["git", "init", "-q", clone], capture_output=True)
    if r.returncode: sys.exit(f"git init 失败:{r.stderr}")
    for args in (("git", "remote", "add", "origin", url),
                 ("git", "fetch", "-q", "--depth", "1", "origin", commit)):
        r = subprocess.run(args, cwd=clone, capture_output=True, text=True)
        if r.returncode: sys.exit(f"拉取 {name} 失败({args[1]}):{r.stderr.strip()}\n检查网络,或上游 {commit[:8]} 是否仍可访问")
    r = subprocess.run(["git", "checkout", "-q", "FETCH_HEAD"], cwd=clone, capture_output=True)
    if r.returncode: sys.exit(f"checkout {name} 失败:{r.stderr}")
    src = clone if sub == "." else os.path.join(clone, *sub.split("/"))
    skill = os.path.join(workdir, name)
    shutil.copytree(src, skill, ignore=shutil.ignore_patterns(".git"))
    got = sha256(os.path.join(skill, "SKILL.md"))
    if got != want:
        sys.exit(f"{name} 校验失败:SKILL.md 哈希与登记锚点不符\n  期望 {want}\n  实际 {got}\n上游可能被改写;核实后更新脚本内登记即可")

def build_root(workdir):
    """合成一个最小 HAnchor 根:additions/08-doc-skills 三技能齐 + 01-user-rules(如有)
    —— collect() 只认 <root>/additions/*/skills/<名>/SKILL.md,基线不存在即零基线技能"""
    root = os.path.join(workdir, "hanchor-root")
    group = os.path.join(root, "additions", "08-doc-skills", "skills")
    os.makedirs(group)
    for name in SKILLS:
        local = os.path.join(GROUP_DIR, "skills", name)
        if os.path.isdir(local):
            shutil.copytree(local, os.path.join(group, name))
            print(f"  · {name}:本仓自带", flush=True)
        elif name in UPSTREAM:
            fetch(name, workdir)
            shutil.move(os.path.join(workdir, name), os.path.join(group, name))
            print(f"  · {name}:已从上游 {UPSTREAM[name][0].rsplit('/', 1)[-1]}@{UPSTREAM[name][1][:8]} 拉取并校验", flush=True)
        else:
            sys.exit(f"{name} 既不在本仓也不在上游登记表")
    rules = os.path.normpath(os.path.join(GROUP_DIR, "..", "..", "01-user-rules", "meta-rules.md"))
    if os.path.isfile(rules):
        dst = os.path.join(root, "additions", "01-user-rules")
        os.makedirs(dst); shutil.copy2(rules, dst)
    return root

def main():
    ap = argparse.ArgumentParser(description="文档三技能一条命令装齐(来源:本仓 + 上游锚点)")
    ap.add_argument("project")
    ap.add_argument("--harness", default="zcode")
    ap.add_argument("--no-rules", action="store_true")
    a = ap.parse_args()
    project = os.path.abspath(a.project)
    if not os.path.isdir(project):
        sys.exit(f"项目目录不存在:{project}")
    workdir = tempfile.mkdtemp(prefix="hanchor-doc-")
    try:
        root = build_root(workdir)
        env = dict(os.environ, HANCHOR_ROOT=root)
        only = ",".join(SKILLS)
        cmd = [sys.executable, os.path.join(HERE, "install_to_project.py"), project,
               "--only", only, "--harness", a.harness] + (["--no-rules"] if a.no_rules else [])
        r = subprocess.run(cmd, env=env)
        sys.exit(r.returncode)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

if __name__ == "__main__":
    main()
