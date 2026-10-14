#!/usr/bin/env python3
"""
差旅补贴计算器

补贴规则：
    补贴金额 = (机票全价金额 - 实际购买金额) × 20%

即：员工购买机票产生的差价（省下的钱），公司按20%比例返还给员工作为差旅补贴。

用法：
    1) 已知 实际购买金额 + 折扣比例（如 7折 / 0.7）：
       python3 calc.py --price 700 --discount 0.7
       python3 calc.py --price 700 --discount 7折

    2) 已知 实际购买金额 + 机票全价：
       python3 calc.py --price 700 --full-price 1000

参数说明：
    --price        实际购买金额（必填）
    --discount     折扣比例。支持两种写法：
                       小数形式，如 0.7（表示按全价的70%购买）
                       "N折" 形式，如 "7折"（等同于0.7）
    --full-price   机票全价金额（如果直接知道全价，可用此参数代替 --discount）

计算逻辑：
    若提供 --discount：
        全价 = 实际购买金额 / 折扣比例
    若提供 --full-price：
        直接使用该数值作为全价

    差价 = 全价 - 实际购买金额
    补贴 = 差价 × 20%
"""

import argparse
import re
import sys


def parse_discount(discount_str: str) -> float:
    """将折扣字符串解析为小数比例，如 '7折' -> 0.7，'0.7' -> 0.7"""
    discount_str = discount_str.strip()
    m = re.match(r'^(\d+(\.\d+)?)\s*折$', discount_str)
    if m:
        return float(m.group(1)) / 10.0
    try:
        val = float(discount_str)
    except ValueError:
        raise ValueError(f"无法解析折扣比例: {discount_str}")
    if val <= 0 or val > 1:
        raise ValueError(f"折扣比例应在 (0, 1] 之间，或使用 'N折' 格式，收到: {discount_str}")
    return val


def main():
    parser = argparse.ArgumentParser(description="差旅补贴计算器：补贴 = (全价 - 实际购买金额) × 20%")
    parser.add_argument("--price", type=float, required=True, help="实际购买金额")
    parser.add_argument("--discount", type=str, help="折扣比例，如 0.7 或 '7折'")
    parser.add_argument("--full-price", type=float, help="机票全价金额（如果直接已知全价）")
    parser.add_argument("--rate", type=float, default=0.20, help="补贴比例，默认0.20（即20%）")

    args = parser.parse_args()

    if args.discount is None and args.full_price is None:
        print("错误：必须提供 --discount 或 --full-price 之一", file=sys.stderr)
        sys.exit(1)

    if args.full_price is not None:
        full_price = args.full_price
    else:
        discount_ratio = parse_discount(args.discount)
        full_price = args.price / discount_ratio

    if full_price < args.price:
        print("警告：计算出的全价小于实际购买金额，请检查输入是否正确。", file=sys.stderr)

    savings = full_price - args.price
    subsidy = savings * args.rate

    print(f"实际购买金额：{args.price:.2f} 元")
    print(f"机票全价金额：{full_price:.2f} 元")
    print(f"差价（全价 - 实际购买）：{savings:.2f} 元")
    print(f"补贴比例：{args.rate * 100:.0f}%")
    print(f"差旅补贴金额：{subsidy:.2f} 元")


if __name__ == "__main__":
    main()
