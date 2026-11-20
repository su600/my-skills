#!/usr/bin/env python3
"""
outlook_cleanup.py — Outlook 低价值邮件清理（通过 Maton API 网关）

按「发件人 + 主题」规则将营销/订阅/系统通知类邮件筛选出来，
默认用 /move 移到「已删除邮件」（软删除、可恢复），绝不硬删。

用法：
  # 1) 扫描收件箱邮件元数据
  python3 outlook_cleanup.py scan --folder Inbox --out /tmp/outlook_inbox.json

  # 2) 分析并生成可删候选清单（含分类统计/发件人排名/抽检）
  python3 outlook_cleanup.py analyze --input /tmp/outlook_inbox.json \
      --out /tmp/outlook_candidates.json

  # 3) 删除（默认 dry-run 只打印；加 --yes 才真正移动）
  python3 outlook_cleanup.py delete --input /tmp/outlook_candidates.json --yes

  # 4) 查看各文件夹数量
  python3 outlook_cleanup.py report

一条龙：python3 outlook_cleanup.py run --yes
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

GATEWAY = "https://gateway.maton.ai/outlook/v1.0"
API = f"{GATEWAY}/me"
HERE = Path(__file__).resolve().parent
RULES_FILE = HERE.parent / "config" / "rules.json"
LOCK_FILE = Path("/tmp/outlook_inbox_cleanup.lock")
APP = "outlook"
DEFAULT_BATCH = 20
TIMEOUT = 60
FIELDS = "subject,from,receivedDateTime,isRead,hasAttachments,categories,importance,bodyPreview"


# ─── 基础设施 ──────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_api_key() -> str:
    key = os.environ.get("MATON_API_KEY", "").strip()
    if key:
        return key
    p = Path("/root/.config/maton/api_key")
    if p.exists():
        key = p.read_text().strip()
        if key:
            os.environ["MATON_API_KEY"] = key
            return key
    r = subprocess.run(["/bin/bash", "-lc", 'source /root/.bashrc >/dev/null 2>&1; printf %s "${MATON_API_KEY:-}"'],
                       capture_output=True, text=True, check=False)
    key = r.stdout.strip()
    if key:
        os.environ["MATON_API_KEY"] = key
        return key
    raise RuntimeError("MATON_API_KEY 未配置（环境变量 / ~/.config/maton/api_key / ~/.bashrc 均未找到）")


def load_rules() -> Dict:
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def _fix_nextlink(url: str) -> str:
    for host in ("https://graph.microsoft.com", "https://outlook.office.com"):
        if url.startswith(host):
            # GATEWAY 已含 /v1.0，这里只替换到 /outlook 前缀
            return "https://gateway.maton.ai/outlook" + url[len(host):]
    return url


def api_request(method: str, url: str, body: Optional[Dict] = None, retries: int = 4) -> Dict:
    key = load_api_key()
    url = _fix_nextlink(url)
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "ConsistencyLevel": "eventual",
    }
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read().decode("utf-8", "replace").strip()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1)); continue
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1)); continue
            raise
    raise RuntimeError(f"请求失败 {url}: {last}")


# ─── 抓取 ──────────────────────────────────────────────

def fetch_messages(folder: str = "Inbox", cap: int = 20000) -> List[Dict]:
    url = (f"{API}/mailFolders/{urllib.parse.quote(folder)}/messages"
           f"?$top=1000&$select={FIELDS}&$orderby=receivedDateTime%20desc")
    out: List[Dict] = []
    page = 0
    while url and len(out) < cap:
        d = api_request("GET", url)
        v = d.get("value", [])
        out.extend(v)
        page += 1
        log(f"  page {page}: +{len(v)} 累计 {len(out)}")
        url = d.get("@odata.nextLink")
    return out


# ─── 分类 ──────────────────────────────────────────────

def _sender(msg: Dict) -> str:
    return ((msg.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()


def _age_days(msg: Dict) -> int:
    try:
        dt = datetime.fromisoformat(msg["receivedDateTime"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:  # noqa: BLE001
        return 99999


def classify(msg: Dict, rules: Dict) -> str:
    """返回 PROMO / NOTIFY / KEEP / OTHER。"""
    addr = _sender(msg)
    subj = msg.get("subject") or ""
    if addr in set(rules.get("keep_senders", [])):
        return "KEEP"
    for pat in rules.get("keep_subject_patterns", []):
        if re.search(re.escape(pat), subj, re.I):
            return "KEEP"
    if any(p.lower() in addr for p in rules.get("promo_patterns", [])):
        return "PROMO"
    if any(p.lower() in addr for p in rules.get("notify_patterns", [])):
        return "NOTIFY" if _age_days(msg) > rules.get("notify_older_than_days", 90) else "OTHER"
    return "OTHER"


def build_candidates(msgs: List[Dict], rules: Dict) -> Dict:
    buckets = defaultdict(list)
    for m in msgs:
        m["_cat"] = classify(m, rules)
        buckets[m["_cat"]].append(m)
    delete = buckets["PROMO"] + buckets["NOTIFY"]
    keep = buckets["KEEP"] + buckets["OTHER"]
    return {"delete": delete, "keep": keep, "counts": {k: len(v) for k, v in buckets.items()}}


def slim(m: Dict) -> Dict:
    return {"id": m.get("id"), "from": _sender(m), "name": ((m.get("from") or {}).get("emailAddress") or {}).get("name", ""),
            "subject": m.get("subject"), "date": m.get("receivedDateTime")}


# ─── 删除（移动到已删除邮件）────────────────────────────

def move_messages(ids: List[str], dest: str = "deleteditems", dry_run: bool = True,
                  batch: int = DEFAULT_BATCH) -> Dict:
    moved = failed = 0
    fails: List[Dict] = []
    for i in range(0, len(ids), batch):
        chunk = ids[i:i + batch]
        if dry_run:
            moved += len(chunk)
            continue
        reqs = [{"id": str(j), "method": "POST",
                 "url": f"/me/messages/{urllib.parse.quote(mid, safe='')}/move",
                 "body": {"destinationId": dest},
                 "headers": {"Content-Type": "application/json"}}
                for j, mid in enumerate(chunk)]
        try:
            r = api_request("POST", f"{GATEWAY}/$batch", {"requests": reqs})
            for x in r.get("responses", []):
                if x.get("status") in (200, 201, 202):
                    moved += 1
                else:
                    failed += 1
                    fails.append({"id": chunk[int(x["id"])], "status": x.get("status"),
                                  "body": str(x.get("body"))[:200]})
        except Exception as e:  # noqa: BLE001
            for mid in chunk:  # 回退逐封
                try:
                    api_request("POST", f"{API}/messages/{urllib.parse.quote(mid, safe='')}/move",
                                {"destinationId": dest})
                    moved += 1
                except Exception as e2:  # noqa: BLE001
                    failed += 1
                    fails.append({"id": mid, "error": str(e2)})
        if (i // batch) % 20 == 0:
            log(f"  进度 {i + len(chunk)}/{len(ids)}  成功={moved} 失败={failed}")
        time.sleep(0.12)
    return {"moved": moved, "failed": failed, "fails": fails}


# ─── 命令 ──────────────────────────────────────────────

def cmd_scan(args) -> int:
    log(f"扫描文件夹 {args.folder} ...")
    msgs = fetch_messages(args.folder, args.cap)
    Path(args.out).write_text(json.dumps(msgs, ensure_ascii=False), encoding="utf-8")
    log(f"共 {len(msgs)} 封 → {args.out}")
    return 0


def cmd_analyze(args) -> int:
    msgs = json.loads(Path(args.input).read_text(encoding="utf-8"))
    rules = load_rules()
    res = build_candidates(msgs, rules)
    delete = res["delete"]
    log(f"总计 {len(msgs)} 封 | 分类：{res['counts']}")
    log(f"建议删除 {len(delete)} 封 | 保留/待定 {len(res['keep'])} 封")
    by = Counter(slim(m)["from"] for m in delete)
    log("\n可删发件人 Top 20：")
    for a, n in by.most_common(20):
        log(f"  {n:>5}  {a}")
    if delete:
        log("\n抽检样本：")
        for m in random.sample(delete, min(15, len(delete))):
            s = slim(m)
            log(f"  {s['from'][:34]:34s} | {(s['subject'] or '')[:50]}")
    Path(args.out).write_text(json.dumps([slim(m) for m in delete], ensure_ascii=False), encoding="utf-8")
    Path(args.keep_out).write_text(json.dumps([slim(m) for m in res["keep"]], ensure_ascii=False), encoding="utf-8")
    log(f"\n候选清单 → {args.out}（{len(delete)} 封）")
    log(f"保留清单 → {args.keep_out}（{len(res['keep'])} 封）")
    return 0


def cmd_delete(args) -> int:
    cands = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ids = [c["id"] if isinstance(c, dict) else c for c in cands]
    if 0 < args.limit < len(ids):
        ids = ids[:args.limit]
    if not ids:
        log("没有可删除的邮件。")
        return 0
    lock_fd = os.open(LOCK_FILE, os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("已有清理任务在运行，退出。")
        return 2
    log(f"{'[DRY RUN] 模拟' if args.dry_run else '开始'}移动 {len(ids)} 封到 {args.dest} ...")
    r = move_messages(ids, args.dest, args.dry_run, args.batch)
    log(f"\n完成：成功 {r['moved']}，失败 {r['failed']}")
    if r["fails"]:
        Path(args.fails_out).write_text(json.dumps(r["fails"], ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"失败明细 → {args.fails_out}")
    if not args.dry_run:
        log("说明：邮件已移入「已删除邮件」，可在 Outlook 恢复。")
    return 0


def cmd_report(args) -> int:
    for f in ("Inbox", "DeletedItems", "JunkEmail", "Archive", "SentItems", "Drafts"):
        try:
            d = api_request("GET", f"{API}/mailFolders/{f}?$select=displayName,totalItemCount,unreadItemCount")
            log(f"  {d.get('displayName', f):12s} 总数={d.get('totalItemCount'):>7} 未读={d.get('unreadItemCount')}")
        except Exception as e:  # noqa: BLE001
            log(f"  {f}: {e}")
    return 0


def cmd_run(args) -> int:
    tmp = Path("/tmp")
    scan_args = argparse.Namespace(folder=args.folder, cap=args.cap, out=str(tmp / "outlook_scan.json"))
    cmd_scan(scan_args)
    an_args = argparse.Namespace(input=scan_args.out, out=str(tmp / "outlook_candidates.json"),
                                 keep_out=str(tmp / "outlook_keep.json"))
    cmd_analyze(an_args)
    if not args.yes:
        log("\n[DRY RUN] 未加 --yes，未执行删除。确认后加 --yes 重跑 run，或执行 delete。")
        return 0
    del_args = argparse.Namespace(input=an_args.out, dest=args.dest, dry_run=False, limit=0,
                                  batch=DEFAULT_BATCH, fails_out=str(tmp / "outlook_fails.json"))
    return cmd_delete(del_args)


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description="Outlook 低价值邮件清理（Maton 网关）")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="抓取邮件元数据")
    s.add_argument("--folder", default="Inbox")
    s.add_argument("--cap", type=int, default=20000)
    s.add_argument("--out", default="/tmp/outlook_scan.json")
    s.set_defaults(func=cmd_scan)

    a = sub.add_parser("analyze", help="分类并生成候选清单")
    a.add_argument("--input", default="/tmp/outlook_scan.json")
    a.add_argument("--out", default="/tmp/outlook_candidates.json")
    a.add_argument("--keep-out", default="/tmp/outlook_keep.json")
    a.set_defaults(func=cmd_analyze)

    d = sub.add_parser("delete", help="移动候选邮件到已删除邮件")
    d.add_argument("--input", default="/tmp/outlook_candidates.json")
    d.add_argument("--dest", default="deleteditems", help="目标文件夹（well-known 名或 id）")
    d.add_argument("--limit", type=int, default=0)
    d.add_argument("--batch", type=int, default=DEFAULT_BATCH)
    d.add_argument("--dry-run", action="store_true", default=False)
    d.add_argument("--yes", action="store_true", help="确认真正执行（否则 dry-run）")
    d.add_argument("--fails-out", default="/tmp/outlook_fails.json")
    d.set_defaults(func=cmd_delete)

    r = sub.add_parser("report", help="查看文件夹数量")
    r.set_defaults(func=cmd_report)

    u = sub.add_parser("run", help="scan + analyze（可选 --yes 删除）")
    u.add_argument("--folder", default="Inbox")
    u.add_argument("--cap", type=int, default=20000)
    u.add_argument("--dest", default="deleteditems")
    u.add_argument("--yes", action="store_true")
    u.set_defaults(func=cmd_run)

    args = p.parse_args(argv)
    if args.cmd == "delete" and not args.dry_run and not args.yes:
        args.dry_run = True
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))