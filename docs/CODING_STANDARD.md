# Coding Standard

> Engineering rules for all current and future contributors.
> Effective: 2026-07-10.

## 适用范围

- 适用于 src 下所有 Python 模块。
- 适用于 tests 下所有测试。
- 适用于 config 下的配置契约。
- 适用于数据库迁移代码。
- 适用于命令行入口。
- 适用于未来 API 服务。
- 文档示例也应遵循安全规则。
- 已有代码逐步迁移而非无关重写。

## PEP 8

- 遵循 PEP 8 基本格式。
- 使用四空格缩进。
- 每行保持合理长度。
- 模块顶部集中 import。
- 标准库、第三方、本地包分组。
- 顶层函数之间留两行。
- 避免尾随空格。
- 格式变化不夹带业务重构。

## Type Hint

- 新增公共函数应提供参数类型。
- 新增公共函数应提供返回类型。
- 复杂字典优先 TypedDict 或 dataclass。
- Optional 只在确实允许 NULL 时使用。
- 数据库 Row 类型需明确兼容。
- 外部 JSON 边界可使用 Mapping。
- 类型不能替代运行时校验。
- 逐步补齐而不强制一次改完旧模块。

## Docstring

- 公共模块应有模块职责说明。
- 公共类应有 docstring。
- 非直观公共函数应有 docstring。
- docstring 描述行为而非重复代码。
- 说明单位与日期格式。
- 说明可能抛出的异常。
- 说明是否执行数据库写入。
- 简单私有辅助函数可省略。

## 命名

- 模块使用 snake_case。
- 函数使用 snake_case。
- 变量使用 snake_case。
- 常量使用 UPPER_SNAKE_CASE。
- 类使用 PascalCase。
- 布尔变量使用 is、has 或 should 语义。
- 日期变量带 date 或 datetime 后缀。
- 单位容易混淆时写入变量名。

## 函数设计

- 单个函数只承担一个主要职责。
- 输入输出尽量显式。
- 纯计算函数避免隐藏数据库访问。
- I/O 与转换逻辑分开。
- 默认参数不得是可变对象。
- 边界处校验外部输入。
- 复用已有 duration 工具。
- 复杂分支拆分为可测试辅助函数。

## 模块边界

- OAuth 只处理授权。
- Polar Client 只封装远端访问。
- Fetch 只编排抓取与文件保存。
- Import 只解析并写 raw 层。
- Daily Metrics 只做日聚合。
- Baseline 只做个人历史统计。
- Recovery Engine 不依赖 Dashboard。
- Dashboard 不直接访问 Polar API。

## 导入规则

- 避免循环引用。
- 优先包内绝对导入。
- 脚本入口可保留兼容 fallback。
- 禁止通过 sys.path hack 修复设计问题。
- 仅在需要时延迟导入。
- 第三方依赖写入 requirements.txt。
- 测试从 src 包导入。
- 删除未使用 import。

## 配置管理

- 配置不得散落硬编码。
- 算法参数集中到 config。
- 路径常量基于项目根目录。
- 环境差异使用环境变量。
- 配置文件必须有加载校验。
- 配置新增字段需要测试。
- 默认值必须有文档。
- 生产 secret 不属于配置 JSON。

## Secret

- Client ID 与 Secret 存在 .env。
- token 存在受控 data 文件。
- 不得把 secret 写进代码。
- 不得把 token 写进测试 fixture。
- 不得打印 access_token。
- 不得打印 refresh_token。
- 错误信息不得回显 authorization code。
- 文档使用占位符。

## 日志与输出

- 命令行输出保持简短。
- 输出记录数量和目标路径。
- 错误输出包含安全状态码。
- 不输出 raw_json。
- 不输出完整远端错误中的凭据。
- 不使用 print 调试遗留。
- 未来统一 logging 时定义级别。
- 用户可见中文保持清晰一致。

## 异常处理

- 定义领域异常而非裸 Exception。
- 保留原始错误上下文但过滤敏感信息。
- 网络错误与解析错误区分。
- 缺失文件给出明确路径。
- 缺失数据不应总是异常。
- 不可恢复配置错误应快速失败。
- 禁止空 except。
- 测试错误路径。

## 数据库操作

- 所有连接通过 src/db.py。
- SQL 不堆积在 Dashboard。
- 写入函数明确 commit 行为。
- 业务键使用参数绑定。
- 不得拼接用户输入到 SQL。
- 动态列名只能来自受控配置。
- 重复任务使用 upsert。
- 删除操作需要明确产品授权。

## Schema 与迁移

- 建表集中在 SCHEMA。
- 列迁移集中管理。
- 新表定义唯一键。
- 新列定义 NULL 语义。
- 迁移必须幂等。
- 测试空库与旧库。
- 复杂迁移建立版本历史。
- 同步 DATABASE 与 DATA_DICTIONARY。

## JSON 与 CSV

- JSON 使用 UTF-8。
- 需要中文时 ensure_ascii=False。
- 解析外部 JSON 容忍容器变化。
- raw 对象完整保存。
- CSV 使用 utf-8-sig 兼容 BOM。
- CSV header 先规范化。
- 无法解析数字返回缺失。
- 不得用字符串拼接模拟 JSON。

## 日期与 Duration

- 日粒度日期使用 YYYY-MM-DD。
- 日期时间尽量使用 ISO 8601。
- duration 原始值可保留 ISO 8601。
- 计算前统一转换秒。
- 睡眠基线单位为小时。
- 训练基线单位为分钟。
- 时区不能被无声丢弃。
- 无效 duration 明确视为缺失或零的领域规则。

## 算法代码

- 公式拆成可单测函数。
- 所有分数 clamp 到 0–100。
- 权重使用可读命名。
- 版本与结果一起返回。
- fallback 路径显式。
- 缺失输入允许部分计算。
- 当天不得进入自身 baseline。
- 算法变化更新 RECOVERY_ENGINE。

## 测试配套

- 新增行为需要测试。
- Bug 修复先补复现测试。
- 数据库测试用临时路径或内存库。
- 网络测试使用 mock session。
- 测试不依赖真实账号。
- 测试命名描述行为。
- 全量 discover 必须通过。
- 测试数量在 CURRENT_STATE 更新。

## 注释

- 只解释不明显的原因。
- 不写逐行翻译式注释。
- 复杂统计块可加方向说明。
- 安全过滤需要注释原因。
- TODO 必须说明触发条件。
- 不保留过期注释。
- SQL 注释避免干扰执行。
- 文档承担长期设计说明。

## 代码审查

- 检查需求范围。
- 检查跨层调用。
- 检查 secret 泄露。
- 检查 NULL 与零。
- 检查单位。
- 检查日期边界。
- 检查幂等性。
- 检查测试和文档同步。

## 完成定义

- 语法编译通过。
- 相关测试通过。
- 全量测试通过。
- 真实路径验证在安全范围完成。
- 业务文件范围符合需求。
- 数据库迁移已验证或明确无迁移。
- CHANGELOG 已更新。
- CURRENT_STATE 已更新。

## Internationalization

- 新增用户可见文本必须进入 `locales/` 并通过统一 translator 读取。
- 页面不得用语言分支复制整段界面。
- 所有语言资源必须拥有相同叶子 key。
- 内部 enum、数据库字段和默认 CSV schema 不得翻译。
- 格式化只发生在显示层；中文和英文均保持公制单位。
- 缺失翻译必须 fallback 并可见，不能静默显示空白。
- 主要 Streamlit 页面必须通过 `scripts/check_i18n_coverage.py`。
