# additional_difficulty

`additional_difficulty` 用一组可组合的函数来衡量手算加减乘除的“额外难度”。模型遵循笔算流程：逐位拆解、计算进位/借位、记录最近做过的运算并给予记忆折扣，全量功能都以 Python 实现提供。

## 功能概览

| 模块 | 作用 | 公开入口 |
| --- | --- | --- |
| `sum_of_two.py` | 估算两数相加的难度，含分拆生成器 | `difficulty_of_sum`, `difficulty_of_sum_of_two`, `two_partitions` |
| `differences.py` | 估算减法难度，支持生成 (minuend, subtrahend) 对 | `difficulty_of_difference`, `differences` |
| `products.py` | 基于质因数分解的乘法难度模型 | `difficulty_of_product`, `difficulty_of_product_of_two`, `ProductsGenerator` |
| `division.py` | 实现长除法难度模型（仅支持整除） | `difficulty_of_long_division`, `fractions` |
| `factoriser.py` | 质因数分解器，供乘法模块复用 | `ErathosthenesFactoriser` |
| `text_to_number.py` | CLI，把单词映射为两位数字串 | 直接运行脚本 |
所有核心函数都允许通过 `radix`（默认 10）和 `cache_size`（默认 3）参数来模拟不同进位制和短期记忆窗口。

## 快速上手

1. 在项目根目录打开 Python 解释器或脚本，直接导入需要的函数：
   ```python
   from additional_difficulty.sum_of_two import difficulty_of_sum_of_two
   print(difficulty_of_sum_of_two(47, 38))  # 5.0
   ```
2. 若想批量探索难度分布，可运行对应脚本，例如 `python additional_difficulty/products.py 840`。
3. 根据需要调整 `radix`、`cache_size` 等参数来模拟不同的教学假设（例如二进制或“记忆力更佳”的学生）。

> 如果要在其他项目中复用，可将 `additional_difficulty` 目录加入 `PYTHONPATH`，或使用 `pip install -e .` 以可编辑方式安装整个包。

## Python API 详情

### 加法 `sum_of_two`
- `two_partitions(n: int) -> Iterator[tuple[int, int]]`：枚举 `n` 的两数拆分 `(x, y)`，其中 `1 \le x \le y` 且 `x + y = n`。
- `difficulty_of_sum(summands: tuple[int, int], radix: int = 10, cache_size: int = 3) -> float`：逐位执行竖式加法，依据数字特性（如偶数相加、倍增）和最近 `cache_size` 次的重复操作来累计难度。
- `difficulty_of_sum_of_two(x: int, y: int, ...) -> float`：对 `difficulty_of_sum` 的便捷封装。

### 减法 `differences`
- `differences(n: int, max_: int)`：生成 `(n+i, i)` 形式的被减数/减数组合，便于批量测试。
- `difficulty_of_difference(minuend: int, subtrahend: int, radix: int = 10, cache_size: int = 3) -> float`：模拟借位、相等位抵消、尾数 9 的特殊处理等情形。结果至少为 1。

### 乘法 `products`
- `ProductsGenerator(factoriser: ErathosthenesFactoriser | None = None)`：包装了 `ErathosthenesFactoriser`，将整数拆成所有可能的两因子组合；对称组合 `(a, b)` 与 `(b, a)` 均会产出，除非 `a == b`。
- `difficulty_of_product(factors: tuple[int, int], radix: int = 10, cache_size: int = 3) -> float`：实现网格乘法，每个格子的大小由 `difficulty_of_product_of_digits` 决定，并调用 `difficulty_of_sum` 聚合部分和。
- `difficulty_of_product_of_two(x: int, y: int, ...) -> float`：`difficulty_of_product` 的二元入口。

### 除法 `division`
- `fractions(n: int, max_: int)`：生成 `(n * i, i)`，用于批量评估 `n*i ÷ i` 风格的练习。
- `difficulty_of_long_division(numerator: int, denominator: int, radix: int = 10, cache_size: int = 3) -> float`：复现长除法的缓冲区、倍数试探与借位步骤。**目前只处理可以整除的情况**，若 `numerator % denominator != 0` 会抛出断言错误。

### 因式分解 `factoriser`
- `ErathosthenesFactoriser`：带缓存的埃拉托斯特尼筛。
  - `factorise(x: int) -> collections.Counter[int]`：返回 `x` 的素因子及指数，并把最新素数写回 `additional_difficulty/primes.json`。
  - `sieve_multiples_of(p: int, bound: int)`：内部方法，用于扩展素数表。

### 其他实用工具
- `text_to_number.py`：`python additional_difficulty/text_to_number.py hello` 会输出 `07 04 11 11 14`（实际为不含空格的两位数字串）。

## 示例
```python
from additional_difficulty.sum_of_two import difficulty_of_sum_of_two
from additional_difficulty.differences import difficulty_of_difference
from additional_difficulty.products import difficulty_of_product_of_two
from additional_difficulty.division import difficulty_of_long_division

print(difficulty_of_sum_of_two(47, 38))        # 5.0
print(difficulty_of_difference(7032, 587))     # 26.0
print(difficulty_of_product_of_two(84, 32))    # 19.0
print(difficulty_of_long_division(840, 35))    # 44.0
```

脚本形式执行可批量获取“关卡”级别：
- `python additional_difficulty/sum_of_two.py 1000` 会列出与 `1000` 相关的难度分布；
- `python additional_difficulty/differences.py 123456 200000` 评估给定范围内的减法；
- `python additional_difficulty/products.py 840` 枚举 `840` 的所有两因子乘法并给出难度；
- `python additional_difficulty/division.py 123456 5000` 逐个评估 `123456 ÷ d`（`d` 为生成器输出）所需的步骤。

## 难度范围与解读
- **起点为 1**：所有函数都会返回 `max(1, raw_score)`，即使是最简单的笔算也被视为一次操作。
- **无固定上限**：难度值会随着位数增长、借/进位次数、乘法格子数量等因素累积，可轻松达到几十甚至上百。可把这些值映射成星级、段位等自定义量表。
- **浮点数或整数**：加法与乘法因为包含“记忆折扣”会输出浮点数；减法/除法目前返回整数。
- **`cache_size` 影响记忆折扣**：较小的缓存只奖励最近的重复运算，增大该值可以模拟熟练的心算者。
- **相对指标**：模型关注“哪个题更难”而非绝对时间，宜与历史结果或学生表现结合使用。

## 约束与扩展建议
- 所有难度都以“操作次数”近似，仅用于相对比较；若需要精确的教学标签，可在上层映射到星级/层级。
- 当 `cache_size` 较小时，重复运算的折扣更明显；增大该值即可模拟“熟练记忆”更好的情况。
- `difficulty_of_long_division` 与 `difficulty_of_product` 会频繁写入 `primes.json` 或大量枚举，若用于 web 服务建议提前 warm-up 并缓存结果。
- 如果需要支持余数或多位被除数推断，请扩展 `difficulty_of_long_division` 以移除整除断言，并为余数分支设计新的计分规则。
