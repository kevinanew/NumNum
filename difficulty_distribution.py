#!/usr/bin/env python3
"""统计 100 以内两数加减题目的难度分布。"""

from __future__ import annotations

import argparse
from collections import Counter

from generator import Problem, ProblemFactory, deduplicate_problems, difficulty


TERMS_LABEL = '100 以内两数加减'


def sample_difficulties(terms: int, amount: int, precision: int) -> tuple[Counter[float], int]:
    """生成指定题型的若干题目，并按精度统计难度。"""
    factory = ProblemFactory(terms=terms, limit=100)
    samples: list[Problem] = []

    while len(samples) < amount:
        problem = factory.create()
        if problem is None or not problem.operators:
            continue
        samples.append(problem)

    unique = deduplicate_problems(samples)

    counter: Counter[float] = Counter()
    for problem in unique:
        level = round(difficulty(problem), precision)
        counter[level] += 1

    return counter, len(unique)


def main() -> None:
    """命令行入口：根据参数采样题目并打印分布。"""
    parser = argparse.ArgumentParser(description='生成题目并统计难度分布。')
    parser.add_argument('--amount', type=int, default=100_000, help='生成样本数量，默认 100000')
    parser.add_argument('--precision', type=int, default=2, choices=range(1, 5), help='难度取值保留的小数位，默认 2 位')
    args = parser.parse_args()

    if args.amount <= 0:
        raise ValueError('amount 必须为正整数')

    counter, unique_total = sample_difficulties(2, args.amount, args.precision)
    print(f'\n题型：{TERMS_LABEL}')
    print(f'生成题目数量：{args.amount}，去重后保留 {unique_total}')
    print('难度分布：')
    for level in sorted(counter):
        count = counter[level]
        ratio = count / unique_total * 100 if unique_total else 0
        print(f'  难度 {level:.{args.precision}f}: {count:>7}  ({ratio:5.2f}%)')


if __name__ == '__main__':
    main()
