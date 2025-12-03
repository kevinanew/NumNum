#!/usr/bin/env python3

"""交互式题目生成脚本。

根据 additional_difficulty 提供的难度模型，生成 100 以内的加减法题目，
并允许通过命令行交互选择题型、题量及难度区间。
"""

from __future__ import annotations

import html
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from weasyprint import HTML as WeasyHTML

from additional_difficulty.differences import difficulty_of_difference
from additional_difficulty.sum_of_two import difficulty_of_sum_of_two


SAMPLE_SIZE_FOR_DISTRIBUTION = 100_000
SAMPLE_PRECISION = 2
# 题库运算始终控制在 100 以内，便于保证加减法不溢出


@dataclass
class Problem:
    """表示一道由多项整数组成的加减算式。"""

    numbers: list[int]
    operators: list[str]

    def statement(self) -> str:
        """返回题目的字符串表示，供终端与网页展示。"""

        parts = [str(self.numbers[0])]
        for operator, number in zip(self.operators, self.numbers[1:]):
            parts.append(f" {operator} {number}")
        parts.append(" = ?")
        return "".join(parts)

    def answer(self) -> int:
        """按照运算符顺序计算题目的答案。"""

        total = self.numbers[0]
        for operator, number in zip(self.operators, self.numbers[1:]):
            if operator == '+':
                total += number
            else:
                total -= number
        return total


def problem_signature(problem: Problem) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """用数列+运算符列描述一道题目，便于去重。"""

    return tuple(problem.numbers), tuple(problem.operators)


def deduplicate_problems(problems: Sequence[Problem]) -> list[Problem]:
    """移除重复题目，仅保留首次出现的组合。"""

    seen: set[tuple[tuple[int, ...], tuple[str, ...]]] = set()
    unique: list[Problem] = []
    for problem in problems:
        signature = problem_signature(problem)
        if signature in seen:
            continue
        seen.add(signature)
        unique.append(problem)
    return unique


@dataclass
class WorksheetMeta:
    """描述导出题单时的标题、副标题与备注。"""

    title: str
    subtitle: str
    note: str


@dataclass
class ExportPlan:
    """描述批量导出的目标文件及份数。"""

    copies: int
    targets: list[Path]


@dataclass
class GenerationRequest:
    """描述用户期望的题量与难度参数。"""

    amount: int
    minus_ratio: int
    min_level: float
    max_level: float


@dataclass
class OperatorPools:
    """按照首个运算符区分题目集合，便于平衡加减占比。"""

    minus: list[tuple[Problem, float]]
    plus: list[tuple[Problem, float]]


class ProblemSelector:
    """封装题目筛选逻辑，便于维护。"""

    def __init__(self, scored_samples: Sequence[tuple[Problem, float]]):
        self.scored_samples = list(scored_samples)

    def consume(self, selected: Sequence[tuple[Problem, float]]) -> None:
        """从题库中移除已分配题目，避免重复使用。"""

        for item in selected:
            try:
                self.scored_samples.remove(item)
            except ValueError:
                continue

    def select(self, request: GenerationRequest) -> list[tuple[Problem, float]]:
        eligible = self._filter_by_difficulty(request)
        if not eligible:
            print('\n未能在难度范围内选出题目，请放宽难度或减少题量。')
            return []

        random.shuffle(eligible)
        pools = self._build_operator_pools(eligible)
        minus_target = round(request.amount * request.minus_ratio / 100)
        plus_target = request.amount - minus_target

        if len(pools.minus) < minus_target:
            print(f"\n减法题仅剩 {len(pools.minus)} 道，无法满足 {minus_target} 道的期望。")
            minus_target = len(pools.minus)
        if len(pools.plus) < plus_target:
            print(f"加法题仅剩 {len(pools.plus)} 道，无法满足 {plus_target} 道的期望。")
            plus_target = len(pools.plus)

        selected: list[tuple[Problem, float]] = []
        random.shuffle(pools.minus)
        random.shuffle(pools.plus)
        selected.extend(pools.minus[:minus_target])
        selected.extend(pools.plus[:plus_target])

        if len(selected) < request.amount:
            # 二次补位不再关心首运算符，最大化利用剩余题目
            remaining = [item for item in eligible if item not in selected]
            random.shuffle(remaining)
            selected.extend(remaining[: request.amount - len(selected)])

        return selected[: request.amount]

    def _filter_by_difficulty(self, request: GenerationRequest) -> list[tuple[Problem, float]]:
        return [
            (problem, level)
            for problem, level in self.scored_samples
            if request.min_level <= level <= request.max_level
        ]

    @staticmethod
    def _build_operator_pools(problems: Sequence[tuple[Problem, float]]) -> OperatorPools:
        minus_pool = [item for item in problems if item[0].operators[0] == '-']
        plus_pool = [item for item in problems if item[0].operators[0] == '+']
        return OperatorPools(minus=minus_pool, plus=plus_pool)


class WorksheetPresenter:
    """负责控制台展示与导出。"""

    def __init__(self, label: str):
        self.label = label

    def show_distribution(self, distribution: Sequence[tuple[float, int]], total: int) -> None:
        print('难度分布：')
        for level, count in distribution:
            if total:
                ratio = count / total * 100
            else:
                ratio = 0
            print(f"  难度 {level:.{SAMPLE_PRECISION}f}: {count:>7}  ({ratio:5.2f}%)")

    @staticmethod
    def report_operator_distribution(problems: Sequence[tuple[Problem, float]]) -> None:
        minus_count = sum(1 for problem, _ in problems if problem.operators[0] == '-')
        plus_count = len(problems) - minus_count
        print(f"\n实际加法/减法分布：加法 {plus_count} 道，减法 {minus_count} 道。")

    @staticmethod
    def print_problem_statements(problems: Sequence[tuple[Problem, float]]) -> None:
        for problem, level in problems:
            print(f"{problem.statement()}  (difficulty={level:.2f})")

    def prepare_export_plan(self) -> ExportPlan:
        copies = prompt_int('需要生成多少份网页', default=1, minimum=1)
        targets = build_export_targets(copies)
        return ExportPlan(copies=copies, targets=targets)

    def export_html(
        self,
        batches: Sequence[Sequence[tuple[Problem, float]]],
        request: GenerationRequest,
        plan: ExportPlan,
    ) -> None:
        html_texts = self._render_batches(batches, request)
        html_exports: list[tuple[Path, str]] = []
        for index, (path, html_text) in enumerate(zip(plan.targets, html_texts), start=1):
            path.write_text(html_text, encoding='utf-8')
            html_exports.append((path, html_text))
            if plan.copies > 1:
                suffix = f"（第 {index} 份）"
            else:
                suffix = ''
            print(f"\n已生成网页{suffix}：{path.resolve()}")
        self.export_pdf(html_exports, plan)
        print()

    def export_pdf_only(
        self,
        batches: Sequence[Sequence[tuple[Problem, float]]],
        request: GenerationRequest,
        plan: ExportPlan,
    ) -> None:
        html_texts = self._render_batches(batches, request)
        print('\n题目不足，跳过网页导出，仅生成 PDF。')
        self.export_pdf([(None, html_text) for html_text in html_texts], plan)

    def export_pdf(
        self,
        html_exports: Sequence[tuple[Path | None, str]],
        plan: ExportPlan,
    ) -> None:
        if not html_exports:
            return

        pdf_path = build_pdf_target()
        documents = []
        for path, html_text in html_exports:
            if path:
                base_url = str(path.parent.resolve())
            else:
                base_url = None
            document = WeasyHTML(string=html_text, base_url=base_url).render()
            documents.append(document)

        pages = [page for document in documents for page in document.pages]
        if not pages:
            return

        documents[0].copy(pages).write_pdf(str(pdf_path))
        print(f"\n已合并生成 PDF：{pdf_path.resolve()}")


def build_export_targets(copies: int) -> list[Path]:
    """根据份数自动生成唯一的输出文件列表。"""

    default_stem = default_output_stem()
    targets: list[Path] = []
    reserved: set[Path] = set()

    for index in range(1, copies + 1):
        if copies == 1:
            name = f"{default_stem}.html"
        else:
            name = f"{default_stem}_{index}.html"
        base = Path(name)
        candidate = ensure_unique_output_path(base, reserved)
        targets.append(candidate)
        reserved.add(candidate.resolve())

    return targets


def build_pdf_target() -> Path:
    """生成用于合并导出的 PDF 路径。"""

    base = Path(f"{default_output_stem()}.pdf")
    return ensure_unique_output_path(base, set())


def ensure_unique_output_path(base: Path, reserved: set[Path]) -> Path:
    """若默认文件已存在，则自动在文件名后追加序号。"""

    candidate = base
    suffix_index = 1
    while True:
        resolved = candidate.resolve()
        if resolved not in reserved and not candidate.exists():
            return candidate
        candidate = candidate.with_name(f"{base.stem}_{suffix_index}{base.suffix}")
        suffix_index += 1


def default_output_stem() -> str:
    """返回基于当天日期的默认文件名前缀。"""

    return f"worksheet_{date.today().isoformat()}"


class ProblemFactory:
    """根据项数与结果上限随机构造题目。"""

    def __init__(self, terms: int, limit: int):
        """配置需要的算式项数与结果上限。"""

        self.terms = terms
        self.limit = limit

    def create(self) -> Problem | None:
        """随机生成一道符合限制的题目，若失败返回 None。"""

        current = random.randint(1, self.limit)
        numbers = [current]
        operators: list[str] = []

        for _ in range(self.terms - 1):
            operator = random.choice(['+', '-'])

            if operator == '+':
                # 避免加法导致当前值超过上限
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
                # 当前值为 0 时不允许再减，强制切换为加法走正向路径
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
    """根据 additional_difficulty 模型计算题目的浮点难度。"""

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
    """把浮点难度格式化为人类可读的字符串。"""

    if value == float('inf'):
        return '∞'
    return f"{value:.2f}".rstrip('0').rstrip('.')


def generate(factory: ProblemFactory, amount: int, min_level: float, max_level: float) -> list[tuple[Problem, float]]:
    """使用题目工厂生成满足数量与难度范围的题目集合。"""

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


def snapshot_difficulty_distribution(
    terms: int,
    sample_size: int = SAMPLE_SIZE_FOR_DISTRIBUTION,
    precision: int = SAMPLE_PRECISION,
) -> tuple[list[tuple[float, int]], list[tuple[Problem, float]]]:
    """随机采样题目以估算指定题型的难度分布，并返回去重后的题库。"""

    factory = ProblemFactory(terms=terms, limit=100)
    samples: list[Problem] = []
    while len(samples) < sample_size:
        problem = factory.create()
        if problem is None or not problem.operators:
            continue
        samples.append(problem)

    unique = deduplicate_problems(samples)

    counts: Counter[float] = Counter()
    scored: list[tuple[Problem, float]] = []
    for problem in unique:
        level = difficulty(problem)
        scored.append((problem, level))
        level_bucket = round(level, precision)
        counts[level_bucket] += 1

    return sorted(counts.items()), scored


def render_html(problems: Sequence[Problem], meta: WorksheetMeta) -> str:
    """将题目渲染成 A4 打印友好的 HTML。"""

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
    """交互式获取整数输入，带默认值与最小值校验。"""

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
    """交互式获取浮点输入，无法解析时提醒重输。"""

    while True:
        raw = input(f"{message} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print('请输入数字。')


def prompt_percentage(message: str, default: int) -> int:
    """获取 0-100 之间的整数百分比。"""

    while True:
        raw = input(f"{message} [{default}%]: ").strip('% ').strip()
        if not raw:
            return default
        if not raw.isdigit():
            print('请输入 0-100 的整数。')
            continue
        value = int(raw)
        if not 0 <= value <= 100:
            print('请输入 0-100 的整数。')
            continue
        return value


def select_mode() -> tuple[int, str]:
    """当前版本固定提供 100 以内两数加减。"""

    print('\n当前仅支持题型：100 以内两数加减。')
    return 2, '100 以内两数加减'


def collect_generation_request() -> GenerationRequest:
    """采集用户输入并转换为结构化的生成请求。"""

    amount = prompt_int('\n需要生成多少道题（至少 1 道）', default=100, minimum=1)
    minus_ratio = prompt_percentage('减法题占比（剩余将自动分配给加法）', default=50)
    min_level = prompt_float('最低难度', default=10.0)
    return GenerationRequest(
        amount=amount,
        minus_ratio=minus_ratio,
        min_level=min_level,
        max_level=float('inf'),
    )


def main() -> None:
    """命令行入口：采集需求、打印分布并生成题目。"""

    terms, label = select_mode()
    presenter = WorksheetPresenter(label)  # 所有输出都交给 presenter，保持入口整洁
    print(f"\n已选择题型：{label}\n")
    print(f"正在基于 {SAMPLE_SIZE_FOR_DISTRIBUTION} 道随机题估算该题型的难度分布……")

    distribution, scored_samples = snapshot_difficulty_distribution(terms)
    # scored_samples 后续将作为题库来源，distribution 仅用于展示
    unique_total = len(scored_samples)
    print(f'去重后保留 {unique_total} 道独特题目。')
    presenter.show_distribution(distribution, unique_total)

    export_plan = presenter.prepare_export_plan()

    request = collect_generation_request()
    print(
        f"\n已收集需求：题量 {request.amount}，减法占比 {request.minus_ratio}%，"
        f"最低难度 {request.min_level}，最高难度 {request.max_level}."
    )

    selector = ProblemSelector(scored_samples)
    print('构建题目筛选器，准备根据难度和运算符分布挑选题目。')

    generation_incomplete = False
    problems_by_copy: list[list[tuple[Problem, float]]] = []
    for copy_index in range(1, export_plan.copies + 1):
        print(f"\n正在为第 {copy_index} 份生成题目……")
        current = selector.select(request)
        if not current:
            print('未能继续生成题目，提前结束。')
            generation_incomplete = True
            break
        selector.consume(current)
        problems_by_copy.append(list(current))

        if len(current) < request.amount:
            generation_incomplete = True
            print(
                f"仅为第 {copy_index} 份选出 {len(current)} 道题。"
                '尝试调低难度或减少题量。'
            )
            break
        else:
            presenter.report_operator_distribution(current)

    if not problems_by_copy:
        return

    if len(problems_by_copy) < export_plan.copies:
        generation_incomplete = True
        print(
            f"\n题库不足，仅生成 {len(problems_by_copy)} 份。"
            '未生成的份数请调整条件后重试。'
        )
        export_plan = ExportPlan(
            copies=len(problems_by_copy),
            targets=export_plan.targets[: len(problems_by_copy)],
        )

    print('\n生成结果：')
    for index, batch in enumerate(problems_by_copy, start=1):
        print(f"\n第 {index} 份题目：")
        presenter.print_problem_statements(batch)

    if generation_incomplete:
        presenter.export_pdf_only(problems_by_copy, request, export_plan)
    else:
        presenter.export_html(problems_by_copy, request, export_plan)


if __name__ == '__main__':
    main()
    def _render_batches(
        self,
        batches: Sequence[Sequence[tuple[Problem, float]]],
        request: GenerationRequest,
    ) -> list[str]:
        html_texts: list[str] = []
        for problems in batches:
            subtitle = (
                f"题量：{len(problems)}  难度：{format_level(request.min_level)} - "
                f"{format_level(request.max_level)}"
            )
            meta = WorksheetMeta(
                title=self.label,
                subtitle=subtitle,
                note='姓名：__________    日期：__________',
            )
            shuffled = list(problems)
            random.shuffle(shuffled)
            html_text = render_html([problem for problem, _ in shuffled], meta)
            html_texts.append(html_text)
        return html_texts
