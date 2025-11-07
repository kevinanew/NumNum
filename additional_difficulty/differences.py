import sys
import collections
from typing import Iterator


def differences(n: int, max_: int) -> Iterator[tuple[int,int]]:
    for i in range(1, max_ - n + 1):
        yield n + i, i


def difficulty_of_difference(minuend: int, subtrahend: int, radix: int = 10, cache_size: int = 3) -> float:
       
    cache: collections.deque[tuple[int, int, int]] = collections.deque([], maxlen=cache_size)

    if minuend < subtrahend:
        minuend, subtrahend = subtrahend, minuend

    m, s = minuend, subtrahend

    
    assert m >= s

    borrow: int = 0
    retval: int = 0

    result, multiplier = 0, 1

    while s > 0 or borrow > 0:
        m, r_m = divmod(m, radix)
        s, r_s = divmod(s, radix)

        tuple_ = (r_m, r_s, borrow)

        r_m -= borrow

        if r_s > r_m:
            borrow = 1
        else:
            borrow = 0

        if r_m == r_s:
            # Zero difference
            pass
        elif r_s + 1 == radix:
            # subtract 9 <=> add 10 & subtract 1
            retval += 1
        elif tuple_ in cache:
            # Recall result of the same operation, recently done. 
            retval += 1
        elif 2*r_s == r_m:
            # Subtract half of self is not so hard.
            retval += min(r_s, 2)
        elif r_m % 2 == 0 and r_s % 2 == 0:
            # subtract 1 if both digits are even
            retval += max(1, r_s - 1)
        else:
            # the borrowed-bit allows larger digits to be subtracted,
            # don't add extra difficulty for the borrow.
            retval += r_s
            # min(r_m - r_s, r_s)


        # Extra operation to add the borrow.
        retval += borrow

        cache.append(tuple_)

        partial_sum_of_diff = radix*borrow + r_m - r_s
        result += partial_sum_of_diff*multiplier


        # Extra operation to store the borrowed bit
        retval += borrow


        multiplier *= radix
        
    result += multiplier * m

    assert result == minuend - subtrahend, f'{result=}, {m} - {s}, {borrow=}, {multiplier=}, {radix=}'

    return max(1, retval)




if __name__ == '__main__':

    N = int((sys.argv[1:2] or ["123_456"])[0])

    MAX = int((sys.argv[2:3] or ["200_000"])[0])

    levels = collections.defaultdict(list)


    for i, (minuend, subtrahend) in enumerate(differences(n=N, max_=MAX)):
        level = difficulty_of_difference(minuend, subtrahend)
        levels[level].append((minuend, subtrahend))
        # if i >= 18:
        #     break





    for level in sorted(levels)[:-1]:
        diffs = levels[level]
        print(f'Level {level} subtractions: {diffs[:4]},..,{diffs[-4:]}')

        # exc_ending_in_5 = list(sums_not_ending_in(sums, [5]))
        # print(f'(exc ending in 5): {exc_ending_in_5[:4]},..,{exc_ending_in_5[-4:]}')


    hardest_level = max(levels)

    hardest_diffs = levels[hardest_level]

    print(f'Hardest subtractions (level: {hardest_level}): {hardest_diffs[:4]},..,{hardest_diffs[-4:]}')


    # hardest_sums_not_ending_in_5 = list(sums_not_ending_in(hardest_sums, [5]))
    # print(f'Hardest sums not ending in 5: {hardest_sums_not_ending_in_5[:4]},..,{hardest_sums_not_ending_in_5[-4:]}')
