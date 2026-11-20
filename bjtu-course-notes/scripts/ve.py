#!/usr/bin/env python3
"""北交大课程平台取流工具。

链路: mis.bjtu.edu.cn (SSO) -> 课程平台 VE 服务（BJTU_VE_URL）-> HLS 流

命令:
  courses                          列出本学期课程
  scheds <课程名或cId>              列出课节（含序号/日期/时间/schedId）
  audio <schedId> <out.mp3>        抽教师音轨并做音量检测
  probe <schedId>                  只做音量检测，不落盘

所有命令输出 JSON（courses/scheds 为数组），便于上层解析。
"""
import json
import os
import re
import html
import subprocess
import sys

import requests

USER = os.environ["BJTU_USER"]
PASS = os.environ["BJTU_PASS"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
VE = os.environ["BJTU_VE_URL"]  # 例如 http://<host>:<port>/ve
XQ = "2026202701"  # 2026-2027 第一学期

# 音量阈值：mean_volume 低于此值视为静音录制（教室麦克风未接入）
SILENT_MEAN_DB = -60.0


def login():
    s = requests.Session()
    s.headers["User-Agent"] = UA
    r = s.get("https://mis.bjtu.edu.cn/auth/nsso/", timeout=30)
    d = dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', r.text))
    d = {k: html.unescape(v) for k, v in d.items()}
    d["username"] = USER
    d["password"] = PASS
    r = s.post("https://sso.bjtu.edu.cn/sso/login", data=d, timeout=30,
               allow_redirects=False)
    s.get(r.headers["Location"], timeout=30)
    s.get("https://mis.bjtu.edu.cn/module/module/28/", timeout=30)
    r = s.get(f"{VE}/back/core/main/index.shtml?method=index&type=qxkt", timeout=30)
    sid = re.search(r'setRequestHeader\("sessionId",\s*\'([0-9A-F]+)\'\)', r.text).group(1)
    s.headers.update({"sessionId": sid, "X-Requested-With": "XMLHttpRequest",
                      "Referer": r.url})
    return s


def courses(s):
    j = s.get(f"{VE}/back/coursePlatform/course.shtml",
              params={"method": "getCourseList", "pagesize": 100, "page": 1,
                      "xqCode": XQ}, timeout=30).json()
    out = []
    for c in j.get("courseList", []):
        out.append({"cId": c["id"], "name": c["name"],
                    "teacher": c["teacher_name"], "courseNum": c["course_num"],
                    "fzId": c["fz_id"]})
    return out


def enter_course(s, c):
    s.get(f"{VE}/back/coursePlatform/coursePlatform.shtml",
          params={"method": "toCoursePlatform", "courseId": c["courseNum"],
                  "dataSource": 1, "cId": c["cId"], "xkhId": c["fzId"],
                  "xqCode": XQ}, timeout=30)


def scheds(s, cid, dedupe=True):
    """列出课节。

    平台会把同一次录制挂两条记录（分别署名不同教师），指向同一个 HLS 流。
    dedupe=True 时按流地址去重，只保留第一条，避免"第几节"数错。
    """
    j = s.get(f"{VE}/back/rp/common/teachCalendar.shtml",
              params={"method": "toDisplyTeachCourses", "courseId": cid},
              timeout=30).json()
    lst = j.get("courseSchedList") or []
    lst.sort(key=lambda x: (x.get("classBeginTime") or "", x.get("id")))

    seen = {}
    out = []
    for c in lst:
        key = None
        if dedupe:
            sm = stream_map(s, c["id"]) or {}
            key = sm.get("teaStreamHlsUrl") or sm.get("stuStreamHlsUrl") or c["id"]
            if key in seen:
                seen[key]["duplicateSchedIds"].append(c["id"])
                continue
        rec = {"index": len(out) + 1, "schedId": c["id"],
               "date": (c.get("classBeginTime") or "")[:10],
               "time": c.get("courseBetween") or "",
               "room": c.get("classRoom") or "",
               "teacher": c.get("teacherName") or "",
               "name": c.get("courseScheName") or "",
               "duplicateSchedIds": []}
        if dedupe:
            seen[key] = rec
        out.append(rec)
    return out


def stream_map(s, sched_id):
    r = s.get(f"{VE}/back/rp/common/teachCalendar.shtml",
              params={"method": "toDisplyCourseSchedDetail",
                      "courseSchedId": sched_id, "userLevel": "1",
                      "userId": "178128"}, timeout=30)
    try:
        return r.json()["res"]["streamMap"]
    except Exception:
        return None


def probe_volume(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                        "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    mean = mx = None
    for line in r.stderr.splitlines():
        if "mean_volume:" in line:
            mean = float(line.split("mean_volume:")[1].split("dB")[0])
        if "max_volume:" in line:
            mx = float(line.split("max_volume:")[1].split("dB")[0])
    return mean, mx


def extract_audio(url, out):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-i", url, "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "libmp3lame", "-b:a", "32k", out],
                   check=True, timeout=3600)


def resolve_course(s, query):
    """按 cId / 课程号 / 课程名（模糊）匹配课程。"""
    cs = courses(s)
    q = query.strip()
    for c in cs:
        if str(c["cId"]) == q or c["courseNum"] == q:
            return c
    hits = [c for c in cs if q in c["name"] or c["name"] in q]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise SystemExit(json.dumps(
            {"error": "课程名不唯一，请指定 cId", "candidates": hits},
            ensure_ascii=False))
    raise SystemExit(json.dumps(
        {"error": "未找到课程", "query": q, "available": cs},
        ensure_ascii=False))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    s = login()

    if cmd == "courses":
        print(json.dumps(courses(s), ensure_ascii=False, indent=1))

    elif cmd == "scheds":
        c = resolve_course(s, sys.argv[2])
        enter_course(s, c)
        dedupe = "--all" not in sys.argv
        print(json.dumps({"course": c,
                          "deduped": dedupe,
                          "scheds": scheds(s, c["cId"], dedupe)},
                         ensure_ascii=False, indent=1))

    elif cmd in ("audio", "probe"):
        sched_id = sys.argv[2]
        sm = stream_map(s, sched_id)
        if not sm:
            print(json.dumps({"error": "无法获取流信息", "schedId": sched_id},
                             ensure_ascii=False))
            return
        url = sm.get("teaStreamHlsUrl") or sm.get("stuStreamHlsUrl")
        if not url:
            print(json.dumps({"error": "无可用音轨", "schedId": sched_id},
                             ensure_ascii=False))
            return
        if cmd == "probe":
            print(json.dumps({"schedId": sched_id, "stream": url,
                              "rpSize": sm.get("rpSize")}, ensure_ascii=False))
            return
        out = sys.argv[3]
        extract_audio(url, out)
        mean, mx = probe_volume(out)
        silent = mean is None or mean < SILENT_MEAN_DB
        print(json.dumps({"schedId": sched_id, "audio": out,
                          "meanDb": mean, "maxDb": mx,
                          "silent": silent,
                          "verdict": "静音录制，跳过" if silent else "有声音，可转写"},
                         ensure_ascii=False))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
