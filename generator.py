#!/usr/bin/env python3

"""交互式题目生成脚本。

根据 additional_difficulty 提供的难度模型，生成 100 以内的加减法题目，
并允许通过命令行交互选择题型、题量及难度区间。
"""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from additional_difficulty.differences import difficulty_of_difference
from additional_difficulty.sum_of_two import difficulty_of_sum_of_two


@dataclass
class Problem:
    numbers: list[int]
    operators: list[str]

    def statement(self) -> str:
        parts = [str(self.numbers[0])]
        for operator, number in zip(self.operators, self.numbers[1:]):
            parts.append(f" {operator} {number}")
        parts.append(" = ?")
        return "".join(parts)

    def answer(self) -> int:
        total = self.numbers[0]
        for operator, number in zip(self.operators, self.numbers[1:]):
            if operator == '+':
                total += number
            else:
                total -= number
        return total


@dataclass
class WorksheetMeta:
    title: str
    subtitle: str
    note: str


class ProblemFactory:
    def __init__(self, terms: int, limit: int):
        self.terms = terms
        self.limit = limit

    def create(self) -> Problem | None:
        current = random.randint(1, self.limit)
        numbers = [current]
        operators: list[str] = []

        for _ in range(self.terms - 1):
            operator = random.choice(['+', '-'])

            if operator == '+':
                available = self.limit - current
                if available <= 0:
                    operator = '-'
                else:
                    operand = random.randint(1, available)
                    current += operand
                    operators.append('+')
                    numbers.append(operand)
                    continue

            if current == 0:
                available = self.limit - current
                if available <= 0:
                    return None
                operand = random.randint(1, available)
                current += operand
                operators.append('+')
                numbers.append(operand)
                continue

            operand = random.randint(1, current)
            current -= operand
            operators.append('-')
            numbers.append(operand)

        return Problem(numbers=numbers, operators=operators)


def difficulty(problem: Problem) -> float:
    total = 0.0
    running = problem.numbers[0]

    for operator, next_number in zip(problem.operators, problem.numbers[1:]):
        if operator == '+':
            total += difficulty_of_sum_of_two(running, next_number)
            running += next_number
        else:
            total += difficulty_of_difference(running, next_number)
            running -= next_number

    return float(total)


def format_level(value: float) -> str:
    if value == float('inf'):
        return '∞'
    return f"{value:.2f}".rstrip('0').rstrip('.')


def generate(factory: ProblemFactory, amount: int, min_level: float, max_level: float) -> list[tuple[Problem, float]]:
    collected: list[tuple[Problem, float]] = []
    attempts = 0
    candidate_target = max(amount * 2, amount)
    limit = candidate_target * 200  # 先扩充候选集，减少后续筛选失败

    balance_single_step = factory.terms == 2
    plus_target = minus_target = plus_count = minus_count = 0
    if balance_single_step:
        half = amount // 2
        plus_target = half
        minus_target = half
        if amount % 2 == 1:
            if random.choice([True, False]):
                plus_target += 1
            else:
                minus_target += 1

    max_per_answer = max(1, (amount + 9) // 10)  # 单个答案最多占 10%
    answer_counts: dict[int, int] = {}

    candidates: list[tuple[Problem, float]] = []
    while len(candidates) < candidate_target and attempts < limit:
        attempts += 1
        problem = factory.create()
        if problem is None or not problem.operators:
            continue

        level = difficulty(problem)
        if min_level <= level <= max_level:
            candidates.append((problem, level))

    if candidates:
        random.shuffle(candidates)
        for problem, level in candidates:
            if len(collected) >= amount:
                break

            operator = problem.operators[0]
            answer = problem.answer()
            if answer_counts.get(answer, 0) >= max_per_answer:
                continue

            if balance_single_step:
                if operator == '+' and plus_count >= plus_target:
                    continue
                if operator == '-' and minus_count >= minus_target:
                    continue

            collected.append((problem, level))
            answer_counts[answer] = answer_counts.get(answer, 0) + 1
            if balance_single_step:
                if operator == '+':
                    plus_count += 1
                else:
                    minus_count += 1

    while len(collected) < amount and attempts < limit:
        attempts += 1
        problem = factory.create()
        if problem is None or not problem.operators:
            continue

        level = difficulty(problem)
        if not (min_level <= level <= max_level):
            continue

        operator = problem.operators[0]
        answer = problem.answer()
        if answer_counts.get(answer, 0) >= max_per_answer:
            continue

        if balance_single_step:
            if operator == '+' and plus_count >= plus_target:
                continue
            if operator == '-' and minus_count >= minus_target:
                continue

        collected.append((problem, level))
        answer_counts[answer] = answer_counts.get(answer, 0) + 1
        if balance_single_step:
            if operator == '+':
                plus_count += 1
            else:
                minus_count += 1

    return collected



def render_html(problems: Sequence[Problem], meta: WorksheetMeta) -> str:
    rows: list[str] = []
    for _, problem in enumerate(problems, start=1):
        statement = problem.statement()
        expression = html.escape(statement).replace('?', '<span></span>')
        rows.append(
            f'    <div class="problem"><span class="expression">{expression}</span></div>'
        )

    grid_html = "\n".join(rows)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{html.escape(meta.title)}</title>
  <style>
    @page {{
      size: A4 portrait;
      margin: 8mm;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
      line-height: 1.35;
      color: #111;
      margin: 0 auto;
      padding: 10mm 12mm 14mm;
      max-width: 208mm;
      background: #fff;
      font-size: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      column-gap: 8mm;
      row-gap: 4mm;
      font-size: 17px;
    }}
    .problem {{
      min-height: 26px;
      padding-bottom: 0;
      display: flex;
      align-items: center;
    }}
    .problem .expression {{
      font-variant-numeric: tabular-nums;
    }}
    footer {{
      margin-top: 16px;
      font-size: 11px;
      color: #888;
    }}
    @media print {{
      body {{
        margin: 0;
        padding: 0;
        max-width: none;
      }}
      .problem {{
        break-inside: avoid;
        page-break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <section class="grid">
{grid_html}
  </section>
</body>
</html>
"""



def prompt_int(message: str, default: int, minimum: int) -> int:
    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            value = default
        else:
            if not raw.isdigit():
                print('请输入整数。')
                continue
            value = int(raw)

        if value < minimum:
            print('输入超出允许范围。')
            continue

        return value


def prompt_float(message: str, default: float) -> float:
    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print('请输入数字。')


def prompt_yes_no(message: str) -> bool:
    while True:
        raw = input(f"{message} (y/n)：").strip().lower()
        if raw in {'y', 'yes', '是'}:
            return True
        if raw in {'n', 'no', '否', ''}:
            return False
        print('请输入 y 或 n。')



def prompt_output_path(message: str, fallback: str) -> Path:
    while True:
        raw = input(f"{message} [{fallback}]: ").strip()
        target = fallback if not raw else raw
        path = Path(target).expanduser()
        if path.is_dir():
            print('请输入文件名而不是目录。')
            continue
        return path



def ensure_html_suffix(path: Path) -> Path:
    if path.suffix.lower() not in {'.html', '.htm'}:
        return path.with_suffix('.html')
    return path


def select_mode() -> tuple[int, str]:
    choices = {
        '1': (2, '100 以内两数加减'),
        '2': (3, '100 以内三数加减'),
        '3': (4, '100 以内四数加减'),
    }
    prompt = "\n请选择题型:\n" + "\n".join(f"  {key}. {label}" for key, (_, label) in choices.items())

    while True:
        print(prompt)
        pick = input('输入对应数字: ').strip()
        if pick in choices:
            terms, label = choices[pick]
            return terms, label
        print('无效选项，请重新输入。')


def main() -> None:
    terms, label = select_mode()
    print(f"\n已选择题型：{label}\n")

    amount = prompt_int('需要生成多少道题（至少 1 道）', default=100, minimum=1)
    min_level = prompt_float('最低难度', default=10.0)
    max_level = float('inf')

    factory = ProblemFactory(terms=terms, limit=100)
    problems = generate(factory, amount * 2, min_level, max_level)

    if not problems:
        print('\n未能在难度范围内生成题目，请放宽难度或减少题量。')
        return

    random.shuffle(problems)
    problems = problems[:amount]

    if len(problems) < amount:
        print(f"\n仅生成 {len(problems)} 道题。尝试调低难度或减少题量。")

    print('\n生成结果：')
    for problem, level in problems:
        print(f"{problem.statement()}  (difficulty={level:.2f})")

    if prompt_yes_no('是否生成可打印网页？'):
        default_name = f"worksheet_{date.today().isoformat()}.html"
        output_path = ensure_html_suffix(prompt_output_path('输出文件名', default_name))
        subtitle = f"题量：{len(problems)}  难度：{format_level(min_level)} - {format_level(max_level)}"
        meta = WorksheetMeta(
            title=label,
            subtitle=subtitle,
            note='姓名：__________    日期：__________'
        )
        html_text = render_html([problem for problem, _ in problems], meta)
        output_path.write_text(html_text, encoding='utf-8')
        print(f'\n已生成网页：{output_path.resolve()}\n')


if __name__ == '__main__':
    main()
