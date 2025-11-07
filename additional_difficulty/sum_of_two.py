import sys
import collections
from typing import Iterator



def two_partitions(n: int) -> Iterator[tuple[int, int]]:
    for i in range(1, (n // 2) + 1):
        yield i, n-i


def difficulty_of_sum_of_digits(d_x: int, d_y: int) -> float:
    if d_x == d_y:
        # doubling can use fast look up in the 2-times table
        return min(d_x, 3)

    if d_x % 2 == 0 and d_y % 2 == 0:
        # subtract 1 if both digits are even
        return max(1, min(d_x, d_y)-1)

    # add the smaller digit to the larger one, 
    # plus the carry bit.
    return min(d_x, d_y, 1)


def difficulty_of_sum(summands: tuple[int, int], radix: int = 10, cache_size: int = 3) -> float:
    
    cache: collections.deque[tuple[int, int, int]] = collections.deque([], maxlen=cache_size)

    x, y = summands

    if y < x:
        x, y = y, x
    
    assert x <= y

    carry = 0
    retval: float = 0.0

    result, multiplier = 0, 1

    while x > 0 or carry > 0:
        x, r_x = divmod(x, radix)
        y, r_y = divmod(y, radix)

        tuple_ = (r_x, r_y, carry)


        if tuple_ in cache:
            retval += 1
        else:
            retval += difficulty_of_sum_of_digits(r_x, r_y)
            # Extra operation to compute the carry.
            retval += carry

        # Extra operation to add the carry.
        retval += carry

        cache.append(tuple_)

        carry, partial_sum = divmod(r_x + r_y + carry, radix)
        result += partial_sum*multiplier


        # Extra operation to store the carry
        retval += carry


        multiplier *= radix
        
    result += multiplier * y

    assert result == sum(summands), f'{result=}, {summands=}, {carry=}, {multiplier=}, {radix=}'

    return max(1,retval)





if __name__ == '__main__':

    N = int((sys.argv[1:2] or ['100_000'])[0])
    levels = collections.defaultdict(list)


    for summands in two_partitions(N):
        level = difficulty_of_sum(summands)
        levels[level].append(summands)



    for level in sorted(levels)[:-1]:
        sums = levels[level]
        print(f'Level {level} sums: {sums[:4]},..,{sums[-4:]}')

        # exc_ending_in_5 = list(sums_not_ending_in(sums, [5]))
        # print(f'(exc ending in 5): {exc_ending_in_5[:4]},..,{exc_ending_in_5[-4:]}')


    hardest_level = max(levels)

    hardest_sums = levels[hardest_level]

    print(f'Hardest sums (level: {hardest_level}): {hardest_sums[:4]},..,{hardest_sums[-4:]}')


    # hardest_sums_not_ending_in_5 = list(sums_not_ending_in(hardest_sums, [5]))
    # print(f'Hardest sums not ending in 5: {hardest_sums_not_ending_in_5[:4]},..,{hardest_sums_not_ending_in_5[-4:]}')


    # print('\n'.join(str(tuple_) for tuple_ in hardest_sums))

def difficulty_of_sum_of_two(x: int, y: int, *args, **kwargs) -> float:
    return difficulty_of_sum((x,y), *args, **kwargs)