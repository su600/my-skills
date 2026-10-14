#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
朝阳区住宅区对应入学服务片查询工具
数据来源：http://xqcx.bjchyedu.cn/ （小学） 和 http://xqcx.bjchyedu.cn/zh/ （初中）

用法：
  1) 模糊搜索小区名，获取系统里的候选全称列表：
     python3 query.py --search "大西洋新城"

  2) 用候选全称之一，查询小学+初中划片结果（会同时查两个接口并聚合输出JSON）：
     python3 query.py --query "广顺北大街33号院（大西洋新城）所有住宅楼"
"""
import argparse
import json
import sys
import urllib.request
import urllib.parse

BASE_URL = "http://xqcx.bjchyedu.cn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
}


def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def http_post(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")


def search(name):
    """模糊搜索候选小区全称，同时查小学和初中的搜索接口（两者返回的候选集合通常一致，取并集）"""
    encoded = urllib.parse.quote(name)
    result = {"primary": [], "middle": []}
    try:
        raw = http_get(f"{BASE_URL}/search2016.jsp?t=p&n={encoded}")
        data = json.loads(raw)
        if data.get("success"):
            result["primary"] = data.get("data", [])
    except Exception as e:
        print(f"[警告] 小学候选搜索失败: {e}", file=sys.stderr)

    try:
        raw = http_get(f"{BASE_URL}/searchz2016.jsp?t=p&n={encoded}")
        data = json.loads(raw)
        if data.get("success"):
            result["middle"] = data.get("data", [])
    except Exception as e:
        print(f"[警告] 初中候选搜索失败: {e}", file=sys.stderr)

    # 合并去重，保持顺序
    merged = []
    seen = set()
    for item in result["primary"] + result["middle"]:
        if item not in seen:
            seen.add(item)
            merged.append(item)

    return merged


def query_one(exact_name):
    """用系统里的精确全称查询小学 + 初中划片结果"""
    out = {"name": exact_name, "primary_school": None, "middle_school": None}

    try:
        raw = http_post(f"{BASE_URL}/search2016.jsp?t=r", {"n": exact_name})
        data = json.loads(raw)
        if data.get("success"):
            out["primary_school"] = {
                "main": data.get("data", []),
                "candidates": data.get("after30", []),
                "duo_xiaopian": bool(data.get("duo")),
            }
    except Exception as e:
        out["primary_school"] = {"error": str(e)}

    try:
        raw = http_post(f"{BASE_URL}/searchz2016.jsp?t=r", {"n": exact_name})
        data = json.loads(raw)
        if data.get("success"):
            out["middle_school"] = {
                "main": data.get("data", []),
                "candidates": data.get("after30", []),
                "duo_xiaopian": bool(data.get("duo")),
            }
    except Exception as e:
        out["middle_school"] = {"error": str(e)}

    return out


def main():
    parser = argparse.ArgumentParser(description="朝阳区学区划片查询工具")
    parser.add_argument("--search", help="模糊搜索小区名，返回候选全称列表")
    parser.add_argument("--query", help="用精确全称查询小学+初中划片结果")
    args = parser.parse_args()

    if args.search:
        candidates = search(args.search)
        print(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2))
    elif args.query:
        result = query_one(args.query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
