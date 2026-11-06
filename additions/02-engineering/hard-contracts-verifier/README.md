# 游戏商城 · 表结构与 gRPC 契约

本轮交付范围：**数据库表结构 + gRPC proto 定义**。不含服务实现，不含运营后台。

---

## 一、产物清单

```
schema/001_init.sql     建表脚本，20 张表
proto/common.proto      通用类型：Money、枚举、RequestContext
proto/catalog.proto     CatalogService    货架 / 商品详情 / 卡片状态（读路径）
proto/promotion.proto   PromotionService  优惠试算 / 我的券
proto/trade.proto       TradeService      下单 / 支付 / 查单 / 关单
proto/wallet.proto      WalletService     钱包余额 / 流水 / 扣减 / 退回（内部）
proto/payment.proto     PaymentCallbackService  法币回调 / 退款回调 / 查单
proto/delivery.proto    DeliveryService   发货 / 补偿重试（内部）
scripts/verify.py       产物校验脚本
```

---

## 二、三条硬约定

1. **金额一律用最小单位 BIGINT 整数**（法币=分，虚拟币=枚），全库无浮点。
   校验脚本会断言 `FLOAT/DOUBLE/REAL` 零出现，`DECIMAL` 仅用于 `fx_rate` 汇率列。
2. **跨外部系统的写操作必须带业务幂等键**，靠 UNIQUE KEY 兜底，不靠业务代码 if 判断。
3. **配置面与交易面逻辑隔离**：`goods` 可随时改，`order_item` 写入即冻结。

---

## 三、表结构总览（20 张）

| 分组 | 表 |
|---|---|
| 币种 | `currency` |
| 商品 | `goods`、`goods_price`、`goods_grant`、`item` |
| 货架 | `shelf_page`、`shelf_block`、`shelf_block_item` |
| 账务 | `wallet`、`wallet_txn`、`purchase_counter`、`user_asset` |
| 促销 | `promotion`、`promotion_target`、`user_coupon` |
| 交易 | `shop_order`、`order_item`、`payment`、`delivery` |
| 审计 | `config_audit_log` |

---

## 四、五个幂等键（本设计的核心）

不是普通索引，是「重复写入被数据库拒绝」的物理保障。缺任何一个都会出事故：

| 唯一键 | 所在表 | 防住的场景 |
|---|---|---|
| `uk_idem` | `wallet_txn` | 虚拟币重复扣款 |
| `uk_client_token` | `shop_order` | 用户狂点导致的重复下单 |
| `uk_channel_txn` | `payment` | 支付网关重复回调 |
| `uk_order_once` | `delivery` | 重复发货，重复发道具 |
| `uk_coupon_once` | `user_coupon` | 一张券核销两次 |

验证方式（可直接跑）：对同一笔订单连扣两次，`SELECT COUNT(*) FROM wallet_txn WHERE biz_id = ?` 必须恒为 1。

---

## 五、已落定的设计决策

- **商品与档位一对一** → 不拆 sku 表。后悔药：`goods.sku_code` 唯一列 + 订单项快照字段，将来拆表时按 `sku_code` 回填，历史订单不用动。
- **多币种两维定价** `goods_price(goods_id, currency_code)`，各币种独立定价，不走汇率折算。
- **法币与虚拟币分成两条结算路径**，`currency.type` 分流；订单**一单一币，禁止混合支付**。
- **游戏币之间不可互换**，钱包彼此独立。
- **限购**按 `(user_id, goods_id, period_key)` 分桶，`period_key = 'L'` 表示终身。
- **优惠**不用万能公式：固定顺序 单品 → 订单 → 券，互斥组 `exclusion_group` 控制叠加，每步明细写入 `order_item.discount_detail`。
- **货架**只存引用 + 展示配置，区块 `type` 为 `banner|grid|hscroll|list|tabs`，前端按 type 分发组件。
- **卡片状态**由后端下发 `GoodsCardStatus`，前端不做业务判断。

---

## 六、校验方式

```bash
C:/Users/harley/.hanchor/binaries/python/envs/default/Scripts/python.exe scripts/verify.py
```

脚本做四件事：

1. 用 `grpc_tools.protoc` **真编译** 7 个 proto，生成 descriptor set 与 Python stub，读出真实 service / message / enum 清单
2. 用 sqlglot 以 MySQL 方言**真解析** DDL，断言表集合与预期完全一致
3. 断言 5 个幂等键全部存在
4. 断言无浮点金额、每张表显式声明 `ENGINE=InnoDB` + `CHARSET=utf8mb4`

当前结果：**ALL PASS**（6 service / 64 message / 8 enum；20 表 / 12 唯一键 / 7 外键 / 1 CHECK）

---

## 七、尚未验证的部分（如实说明）

**DDL 只通过了 sqlglot 语法解析，没有在真实 MySQL 8 上执行过。**
本机有 mysql 客户端但无 mysqld，Docker 已安装但守护进程未启动。

启动 Docker Desktop 后，用下面两条命令可完成真实执行验证：

```bash
docker run -d --name shop-mysql \
  -e MYSQL_ROOT_PASSWORD=shop_dev_pw \
  -e MYSQL_DATABASE=shop \
  -p 3306:3306 mysql:8.0

mysql -h127.0.0.1 -uroot -pshop_dev_pw shop < schema/001_init.sql
```

语法解析能覆盖类型、主键、唯一键、外键、CHECK、ENUM、JSON、字符集等全部构造，
但**无法**验证：外键引用的表顺序、CHECK 约束在 MySQL 8.0.16 以下被静默忽略、
索引长度是否超出 InnoDB 上限。这三项只在真实执行时才会暴露。

---

## 八、下一步

1. 真实 MySQL 执行验证（需 Docker 起来）
2. `schema/002_seed.sql`：3 个币种 + 商品 + 一个货架页的种子数据
3. M2 商城读路径服务实现
4. M3 交易路径实现（含幂等与并发的可复现测试）
