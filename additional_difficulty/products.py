import sys
import math
import collections
import itertools
from typing import Iterator

from additional_difficulty.factoriser import ErathosthenesFactoriser
from additional_difficulty.sum_of_two import difficulty_of_sum



class ProductsGenerator:
    def __init__(self, factoriser : ErathosthenesFactoriser | None = None):
        self.factoriser = factoriser or ErathosthenesFactoriser()


    def two_products(self, n: int) -> Iterator[tuple[int, int]]:
        
        prime_factorisation: collections.Counter[int] = self.factoriser.factorise(n)
        
        yield from self._two_factor_products(prime_factorisation)


    def _two_factor_products(self, prime_factorisation: collections.Counter[int]) -> Iterator[tuple[int, int]]:
        prime, exponent = prime_factorisation.popitem()

        for i in range((exponent // 2) + 1):
            if prime_factorisation:
                factors = self._two_factor_products(prime_factorisation)
            else:
                factors = iter([(1, 1)])
            
            for a, b in factors:
                yield a * (prime ** i), b * (prime ** (exponent - i))
                if a == b:
                    continue
                
                yield b * (prime ** i), a * (prime ** (exponent - i))


def digits(x: int, radix: int = 10) -> Iterator[int]:
    while x:
        x, r = divmod(x, radix)
        yield r


def difficulty_of_product_of_digits(d_1: int, d_2: int, radix: int = 10) -> int:
    
    product = d_1 * d_2
    
    if product == 0 or 1 in (d_1, d_2):
        return 1

    if product <= radix:
        # 2*3, ..., 2*5 and 3*3
        return 2 

    if any(radix % x == 0 for x in (d_1, d_2)) or product <= 2.4 * radix:
        # 2, 5 or a power of 2
        return 3

    if product == 49:
        return 5

    return 4

    



def difficulty_of_product(factors: tuple[int, int], radix: int = 10, cache_size = 3) -> float:
    
    cache: collections.deque[tuple[int, int, int]] = collections.deque([], maxlen=cache_size)

    a, b = factors

    if a > b:
        a, b = b, a
    
    assert a <= b

    if a == 1:
        return 1

    retval: float = 0.0

    result, multiplier = 0, 1

    # Grid multiplication.
    for (i, d_a), (j, d_b) in itertools.product(
                                        enumerate(digits(a)),
                                        enumerate(digits(b)),
                                        ):

        tuple_ = (d_a, d_b)

        if tuple_ in cache:
            retval += 1
        else:
            retval += difficulty_of_product_of_digits(d_a, d_b)
            # TODO: cache.append(tuple_)

        partial_sum = d_a * d_b * (radix ** (i + j))


        retval += difficulty_of_sum((result, partial_sum), radix, cache_size)

        result += partial_sum

    assert result == math.prod(factors), f'{result=}, {math.prod(factors)=}'


    return max(1, retval)

if __name__ == '__main__':


    if len(sys.argv) >= 2:
        N = int(sys.argv[1])
    else:
        N = 100_000

    levels = collections.defaultdict(list)


    prod_gen = ProductsGenerator()

    # print(f'Factors: {list(prod_gen.two_products(N))}')
    
    for factors in prod_gen.two_products(N):
        level = difficulty_of_product(factors)
        levels[level].append(factors)





    for level in sorted(levels)[:-1]:
        products = levels[level]
        print(f'Level {level} products: {products}')



    hardest_level = max(levels)

    hardest_products = levels[hardest_level]


    print(f'Hardest Level (level {hardest_level}) products: {hardest_products}')

def difficulty_of_product_of_two(x: int, y: int, *args, **kwargs) -> float:
    return difficulty_of_product((x, y), *args, **kwargs)