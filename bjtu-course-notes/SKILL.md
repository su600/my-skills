---
name: bjtu-course-notes
description: 替用户登录北京交通大学课程平台（mis.bjtu.edu.cn → 交大课程平台），下载指定课程某一节课的课堂录制，转写教师音轨，整理成结构化课堂笔记，并邮件发送给用户及指定收件人。当用户说"帮我听第X节课""整理某门课的课堂笔记""把某节课录下来做笔记发我邮箱"，或提到课程名 + 第几节/第几周/某日期时使用。用户重点关注课程事务、考试、作业安排，这些内容必须加粗提醒。
compatibility: 需要 Python 3、requests、faster-whisper、ffmpeg、Gmail 应用专用密码文件 /root/GMAIL_APP_PASSWORD.txt，以及能访问 mis.bjtu.edu.cn 与课程平台 VE 服务的网络。
---

# 北交大课程平台 · 课堂笔记流水线

把"某门课的第 N 节课"变成一份结构化 Markdown 笔记，并发到指定邮箱。

## 固定参数

| 项 | 值 |
|---|---|
| 平台账号 | 环境变量 `BJTU_USER` / `BJTU_PASS`（不要写入文件或聊天） |
| 课程平台地址 | 环境变量 `BJTU_VE_URL` |
| 学期 | `2026202701`（2026-2027 第一学期） |
| 收件人 | `<收件人邮箱>`（可多个） |
| 发件人 | 环境变量 `BJTU_MAIL_SENDER`（Gmail SMTP，密码在 `/root/GMAIL_APP_PASSWORD.txt`） |
| 工作目录 | `/root/course-notes/`（`transcript/`、`notes/`） |
| 脚本目录 | 本 skill 的 `scripts/` |

## 用户偏好（必须遵守）

1. **课程事务、考试、作业、大作业、汇报、提交截止、评分方式、考勤** —— 这些内容在笔记正文中**必须加粗**，并在笔记开头单独做一个「⚠️ 课程事务速览」表格集中列出。
2. 邮件正文必须包含：**这堂课的大概内容** + **重点课程事务**。
3. 笔记要带时间戳，方便回看原视频。
4. 转写有同音错字，必须按上下文修正，并在文末附术语纠错对照表。
5. 拿不准的内容**如实标注为待确认**，不要编造。

## 执行流程

### 步骤 1 · 定位课程与课节

```bash
cd /root/.pi/agent/skills/bjtu-course-notes/scripts
python3 ve.py courses                      # 列出本学期课程，拿到 cId
python3 ve.py scheds "<课程名或cId>"        # 列出课节：index / date / time / schedId
```

- 课程名支持模糊匹配；若返回 `error: 课程名不唯一`，用返回的 `candidates` 里的 `cId` 重试。
- 课节按上课时间升序编号，`index` 即"第几节"。
- **默认已按 HLS 流地址去重**：平台会把同一次录制挂两条记录（分别署名不同教师），指向同一个流。去重后 `duplicateSchedIds` 会列出被合并的 schedId。加 `--all` 可看原始全量。
- 用户说"第 8 周"时，按 `date` 匹配该周的那一节课（去重后每周一节）。
- 用户说具体日期时，按 `date` 精确匹配。
- 用户说"第 N 节"时，直接用 `index == N`。

### 步骤 2 · 抽音频 + 音量检测

```bash
python3 ve.py audio <schedId> /root/course-notes/audio/<schedId>.mp3
```

输出 JSON 含 `meanDb` / `silent` / `verdict`。

> ⏱ **耗时提醒**：拉 HLS 并转码 90 分钟音频约需 **8~12 分钟**，前台调用请给足 timeout（≥900s），或同样放后台跑。不要用 300s 超时，会误判为失败。

- `silent: true`（meanDb < -60）说明该次录制教室麦克风未接入，**是废录制**。此时：
  - 不要转写（会得到幻觉文本）；
  - 告知用户该节无有效音频，并询问是否换一节或跳过。
- 正常录制 `meanDb` 一般在 -15 ~ -30 之间。

### 步骤 3 · 转写（后台跑，约 3.3x 实时）

115 分钟音频约需 35 分钟。**必须后台执行**，不要前台阻塞：

```bash
cd /root/.pi/agent/skills/bjtu-course-notes/scripts
nohup python3 asr.py /root/course-notes/audio/<schedId>.mp3 \
  /root/course-notes/transcript <schedId> \
  --prompt "以下是<课程名>课程的中文课堂讲解，涉及<领域术语>。" \
  > /tmp/asr_<schedId>.log 2>&1 &
```

- 用 `--prompt` 传入课程领域术语，能显著降低专有名词错字率。
- 轮询 `/tmp/asr_<schedId>.log`，看到 `[asr] done` 即完成。
- 完成后删除音频释放磁盘：`rm -f /root/course-notes/audio/<schedId>.mp3`（磁盘常年紧张，务必清理）。

### 步骤 4 · 写笔记

读取 `/root/course-notes/transcript/<schedId>.txt`（逐行带 `[MM:SS]` 时间戳），按 `reference/note-template.md` 的结构写笔记，输出到：

```
/root/course-notes/notes/<课程名>-第<N>次课-<schedId>.md
```

写作要求：

- **开头必须有「⚠️ 课程事务速览」表格**，把考试/作业/汇报/截止/评分/考勤全部集中列出，带时间戳。本节没有就明确写"本节未提及"。
- 正文中凡是提到课程事务、考试、作业的地方，**用 `**加粗**` 标出**。
- 每个小节标题后带 `（MM:SS）` 时间戳。
- 技术内容按"概念 → 原理 → 结论"组织，多用表格对比，保留老师强调的"为什么"。
- 文末附「ASR 术语纠错对照」表 + 「待确认项」。
- 页脚注明生成 Agent 与模型（从 `PI_MODEL` 环境变量读取真实值）。

### 步骤 5 · 发邮件

写一个 spec JSON（避免中文在 shell 里转义出错）：

```bash
cat > /tmp/mail_spec.json <<'JSON'
{
  "to": ["<收件人邮箱>"],
  "subject": "课堂笔记｜<课程名> · 第<N>次课（<日期>）",
  "plain": "……纯文本正文……",
  "html": "……HTML 正文……",
  "attachments": ["/root/course-notes/notes/<文件名>.md"]
}
JSON
python3 /root/.pi/agent/skills/bjtu-course-notes/scripts/send_mail.py /tmp/mail_spec.json
```

邮件正文结构（HTML + 纯文本双版本，正文 16px 以上，行高 1.7）：

1. 称呼：`<称呼>，您好：`
2. 📎 说明附件名称
3. **本堂课大概内容** —— 3~5 条要点，覆盖主要主题
4. **⚠️ 重点课程事务** —— 考试/作业/汇报/截止，逐条列出；没有就写"本节未提及"
5. 说明术语已纠错、待确认项已标注
6. 落款：`发送人：Pi 编码助手 · 使用模型：<PI_MODEL 真实值>`

发送成功后报告：发件人、收件人、主题、附件名与大小。**不要声称已送达**，只说 SMTP 提交成功。

## 常见问题

| 现象 | 处理 |
|---|---|
| `ve.py` 返回"会话结束" | 重新执行命令即可，脚本每次都会重新登录 |
| `scheds` 返回空数组 | 该课程本学期无录制，告知用户 |
| `audio` 报 `无可用音轨` | 该节无视频，跳过 |
| `meanDb` 极低（< -60） | 废录制，跳过并告知 |
| 转写出现大段重复/幻觉 | 该段音频是静音或噪声，笔记中标注"该段转写质量差，未纳入" |
| 磁盘不足 | `rm -rf /root/.cache/pip`，并删除已处理完的音频 |

## 已知坑

- 平台**没有字幕接口**（`getSubtitleFile` 返回"操作异常"），只能走 ASR。
- 教师音轨（`teaStreamHlsUrl`）比学生音轨干净，优先用教师音轨。
- HLS 流**无需鉴权**，ffmpeg 可直接拉。
- 部分课节是同一节课的重复录制（`rpSize` 相同），注意去重。
- 转写速度受内存影响大：机器只有 2 vCPU / 1.9GB RAM，swap 一涨速度就掉到 1x 以下。跑 ASR 时不要同时跑其他重任务。
