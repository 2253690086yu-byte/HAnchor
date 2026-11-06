"""产物校验脚本

proto 侧：真编译（grpc_tools.protoc 生成 descriptor set + Python stub），
         再从 descriptor 里读出真实的 service / message / enum 清单。
sql  侧：MySQL 方言真解析，并对四条设计不变量做断言。

用法：
    C:/Users/harley/.hanchor/binaries/python/envs/default/Scripts/python.exe scripts/verify.py
"""

import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROTO_DIR = ROOT / "proto"
SCHEMA = ROOT / "schema" / "001_init.sql"

# ---- 断言目标：与设计文档一致，改动 schema 时必须同步 ----
EXPECTED_TABLES = {
    "currency", "item", "goods", "goods_price", "goods_grant",
    "shelf_page", "shelf_block", "shelf_block_item",
    "wallet", "wallet_txn", "purchase_counter", "user_asset",
    "promotion", "promotion_target", "user_coupon",
    "shop_order", "order_item", "payment", "delivery", "config_audit_log",
}
# 这些唯一键不是普通索引，而是幂等保证的载体，缺一个就有重复写入风险
EXPECTED_IDEMPOTENCY_KEYS = {
    "uk_idem",          # 钱包扣减
    "uk_client_token",  # 下单
    "uk_channel_txn",   # 支付回调
    "uk_order_once",    # 发货
    "uk_coupon_once",   # 券核销
}
# 金额禁用浮点
FORBIDDEN_TYPES = ("FLOAT", "DOUBLE", "REAL", "DECIMAL(", "NUMERIC(")
# DECIMAL 的例外：汇率 fx_rate 允许 DECIMAL（它不是金额）
DECIMAL_ALLOWLIST = ("fx_rate",)

FAILED = []


def fail(msg):
    FAILED.append(msg)
    print(f"  ✗ {msg}")


def strip_comments(sql: str) -> str:
    """去掉 -- 行注释，避免正则从注释里误抓（Python 的 \\w 会匹配中文）"""
    return "\n".join(
        line for line in sql.splitlines()
        if not line.lstrip().startswith("--")
    )


def check_proto():
    from grpc_tools import protoc

    protos = sorted(p.name for p in PROTO_DIR.glob("*.proto"))
    if not protos:
        fail("proto 目录为空")
        return
    print(f"[proto] 编译 {len(protos)} 个文件")

    with tempfile.TemporaryDirectory() as td:
        desc = os.path.join(td, "shop.desc")
        args = [
            "protoc", f"-I{PROTO_DIR}",
            f"--descriptor_set_out={desc}", "--include_imports",
            f"--python_out={td}", f"--grpc_python_out={td}",
        ] + [str(PROTO_DIR / p) for p in protos]

        if protoc.main(args) != 0:
            fail("protoc 编译失败")
            return

        pb2 = sorted(f for f in os.listdir(td) if f.endswith("_pb2.py"))
        grpc = sorted(f for f in os.listdir(td) if f.endswith("_pb2_grpc.py"))
        print(f"  ✓ 生成 {len(pb2)} 个 _pb2.py / {len(grpc)} 个 _pb2_grpc.py")

        from google.protobuf import descriptor_pb2
        fds = descriptor_pb2.FileDescriptorSet()
        fds.ParseFromString(pathlib.Path(desc).read_bytes())

        services, messages, enums = [], 0, 0
        for f in fds.file:
            services += list(f.service)
            messages += len(f.message_type)
            enums += len(f.enum_type)

        print(f"  ✓ {len(fds.file)} 文件 / {len(services)} service / "
              f"{messages} message / {enums} enum")
        for s in services:
            print(f"      · {s.name:<24} {len(s.method)} 个方法")
        # 每个 proto 文件都必须有 package，否则跨语言生成会撞命名空间
        for f in fds.file:
            if not f.package:
                fail(f"{f.name} 缺少 package 声明")


def check_sql():
    import sqlglot

    raw = SCHEMA.read_text(encoding="utf-8")
    body = strip_comments(raw)

    try:
        stmts = [s for s in sqlglot.parse(raw, read="mysql") if s is not None]
    except Exception as e:  # noqa: BLE001
        fail(f"SQL 解析异常：{e}")
        return

    print(f"[sql ] MySQL 方言解析通过，{len(stmts)} 条语句")

    tables = set(re.findall(r"CREATE TABLE (\w+)", body))
    uniques = set(re.findall(r"UNIQUE KEY ([A-Za-z0-9_$]+)", body))
    fks = re.findall(r"CONSTRAINT ([A-Za-z0-9_$]+) FOREIGN KEY", body)
    checks = re.findall(r"CONSTRAINT ([A-Za-z0-9_$]+) CHECK", body)

    # 不变量 1：表集合完全一致
    missing, extra = EXPECTED_TABLES - tables, tables - EXPECTED_TABLES
    if missing:
        fail(f"缺少表：{sorted(missing)}")
    if extra:
        fail(f"多出未登记的表：{sorted(extra)}")
    if not missing and not extra:
        print(f"  ✓ {len(tables)} 张表与预期清单完全一致")

    # 不变量 2：五个幂等键必须全部存在
    miss_idem = EXPECTED_IDEMPOTENCY_KEYS - uniques
    if miss_idem:
        fail(f"缺少幂等键：{sorted(miss_idem)}")
    else:
        print(f"  ✓ {len(EXPECTED_IDEMPOTENCY_KEYS)} 个幂等键全部就位："
              f"{', '.join(sorted(EXPECTED_IDEMPOTENCY_KEYS))}")
    print(f"  · 唯一键共 {len(uniques)} 个 / 外键 {len(fks)} 个 / CHECK {len(checks)} 个")

    # 不变量 3：金额禁用浮点（DECIMAL 仅允许汇率列）
    float_lines = [
        ln.strip() for ln in body.splitlines()
        if any(t in ln.upper() for t in ("FLOAT", "DOUBLE", "REAL"))
    ]
    decimal_lines = [
        ln.strip() for ln in body.splitlines()
        if "DECIMAL(" in ln.upper() and not any(a in ln for a in DECIMAL_ALLOWLIST)
    ]
    if float_lines:
        fail(f"出现浮点类型：{float_lines}")
    elif decimal_lines:
        fail(f"非汇率列使用了 DECIMAL：{decimal_lines}")
    else:
        print("  ✓ 无浮点金额；DECIMAL 仅用于 fx_rate 汇率")

    # 不变量 4：每张表都显式指定存储引擎与字符集
    bad = [t for t in tables
           if f"CREATE TABLE {t}" not in body
           or not re.search(
               rf"CREATE TABLE {t}\b.*?ENGINE=InnoDB[^;]*CHARSET=utf8mb4",
               body, re.S)]
    if bad:
        fail(f"未显式声明 InnoDB/utf8mb4：{sorted(bad)}")
    else:
        print(f"  ✓ {len(tables)} 张表均显式声明 ENGINE=InnoDB + CHARSET=utf8mb4")


if __name__ == "__main__":
    check_proto()
    print("-" * 68)
    check_sql()
    print("-" * 68)
    if FAILED:
        print(f"RESULT: FAILED（{len(FAILED)} 项）")
        for m in FAILED:
            print("  -", m)
        sys.exit(1)
    print("RESULT: ALL PASS")
