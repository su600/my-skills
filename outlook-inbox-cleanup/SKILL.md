---
disable-model-invocation: true
name: outlook-inbox-cleanup
description: 通过 Maton API 网关批量清理 Outlook 收件箱里的低价值邮件（营销推广、订阅简报、系统通知），按可维护规则筛选并给出候选清单，确认后移动到「已删除邮件」（软删除、可恢复）。Use when the user asks to 清理邮箱 / 筛选可删除邮件 / 邮箱瘦身 / 找垃圾订阅 / clean up Outlook inbox / delete newsletters and promotions, or asks to reuse the "低价值邮件清理标准". Also use when operating or maintaining the scheduled inbox cleanup job.
---

# Outlook Inbox Cleanup（低价值邮件清理）

把「扫描 → 分类 → 人工确认 → 软删除」这套标准流程封装成可复用技能。

## 核心原则（重要）

1. **只做软删除**：用 `POST /me/messages/{id}/move`（`destinationId=deleteditems`）把邮件移到「已删除邮件」，**绝不使用 DELETE 硬删**。
   - ⚠️ 注意：Maton 网关上的 `DELETE /me/messages/{id}` 会**绕过「已删除邮件」直接落到 Recoverable Items**（虽仍可恢复，但不是常规路径）。本 skill 一律用 `move`。
2. **先看清单再删**：默认 `dry-run`，必须显式 `--yes` 才真正执行。
3. **规则可维护**：所有判断集中在 `config/rules.json`（个人版本不入库，从 `config/rules.example.json` 复制后修改），不含任何密钥。
4. **保命白名单**：交易/账单、安全/账号、证书/考试、招聘、行程票据等一律保留（`keep_senders` + `keep_subject_patterns`），优先级最高。

## 鉴权

需要 `MATON_API_KEY`。读取顺序：环境变量 → `~/.config/maton/api_key` → `source ~/.bashrc`。
Outlook 连接需已在 maton.ai 侧完成 OAuth（app = `outlook`）。

## 使用流程

```bash
cd <skill-dir>

# 1) 扫描收件箱
python3 scripts/outlook_cleanup.py scan --folder Inbox --out /tmp/outlook_scan.json

# 2) 分类 + 生成候选清单（打印统计/发件人排名/抽检）
python3 scripts/outlook_cleanup.py analyze --input /tmp/outlook_scan.json \
    --out /tmp/outlook_candidates.json --keep-out /tmp/outlook_keep.json

# 3) 先 dry-run 核对，再加 --yes 执行
python3 scripts/outlook_cleanup.py delete --input /tmp/outlook_candidates.json
python3 scripts/outlook_cleanup.py delete --input /tmp/outlook_candidates.json --yes

# 一条龙（不加 --yes 只到分析）
python3 scripts/outlook_cleanup.py run --yes

# 查看各文件夹数量
python3 scripts/outlook_cleanup.py report
```

## 分类标准（rules.json）

| 类别 | 判定 | 动作 |
|---|---|---|
| `KEEP` | 发件人在 `keep_senders`，或主题命中 `keep_subject_patterns` | 保留（最高优先级） |
| `PROMO` | 发件人命中 `promo_patterns` | 删除 |
| `NOTIFY` | 发件人命中 `notify_patterns` 且早于 `notify_older_than_days` | 删除 |
| `OTHER` | 其余 | 不动（人工判断） |

调整方式：直接编辑 `config/rules.json` 增删域名/地址/关键词。

## 输出物

| 文件 | 内容 |
|---|---|
| `/tmp/outlook_scan.json` | 邮件元数据快照 |
| `/tmp/outlook_candidates.json` | 可删候选（含 id/发件人/主题/时间） |
| `/tmp/outlook_keep.json` | 保留清单 |
| `/tmp/outlook_fails.json` | 失败明细（仅在有失败时） |

## 安全与运维

- 有文件锁 `/tmp/outlook_inbox_cleanup.lock`，防止并发重复执行。
- 批量移动走 `$batch`（默认 20/批），失败自动回退逐封，遇 429/5xx 自动重试。
- 恢复方式：Outlook → 已删除邮件 → 顶部「恢复已删除项目」。
- 保留期通常 30 天，过期后才会真正清掉。

## 关联

- `outlook-toolkit`：日历/邮件查询（含时区处理）
- `outlook-github-cleanup`：专门清理 GitHub 通知（同样走 move 软删除）
- `api-gateway`：Maton 网关总入口

---
*维护者：小火箭 🚀*