import sys
import json
import math
import pathlib
import collections
from typing import Iterator, Iterable


class ErathosthenesFactoriser:

    # not primes, sieved out
    # composites = set()
    # Stand in for an OrderedSet 
    composites: dict[int, None] = {}

    cache_file = pathlib.Path(__file__).parent / 'primes.json'

    primes = [2, 3,] #5, 7, 11, 13, 
             # 17, 19, 23, 29, 31]

    # must be odd
    all_primes_known_up_to_inclusive = 3 #31

    def __init__(self, primes: list[int] | None = None):


        # TODO: Make this update the class variable
        # instead of replacing it.
        if primes is not None:
            self.primes = primes
        else:
            try:
                with self.cache_file.open('rt') as f: 
                    cache = json.load(f)
                    self.primes = cache['primes']
                    self.all_primes_known_up_to_inclusive = cache['all_primes_known_up_to_inclusive']

            except:
                # Use ErathosthenesFactoriser.primes 
                pass 



        assert any(x % 2 for x in self.primes), "ErathosthenesFactoriser.primes must contain 3"
        assert self.primes[0] == 2 and self.primes[1] == 3, """primes must contain 2 and 3, and 
                                                               be in ascending order, (and 1 is 
                                                               not a prime by convention)""".replace('  ','')

    def factorise(self, x: int) -> collections.Counter[int]:  # dict[int, int]
        """  Side effects:
              - updates cached primes
              - saves factorisation in prime_factorisation
        """

        start_x = x

        prime_factorisation: collections.Counter[int] = collections.Counter()

        # Factor out 2s now, so we when testing prime candidates
        # the highest known prime is always odd, and we can 
        # always skip forward 2 at a time from it.
        while x % 2 == 0:
            prime_factorisation.update([2])
            x //= 2

        assert x % 2,  f"All 2s should've been factored from {x=}: {start_x=}, {prime_factorisation=}"

        test_up_to_inclusive = math.isqrt(x)

        # 2s already factored out.  Start from primes[1] == 3
        i = 1

        while True:

            r = 0
            p = self.primes[i]



            q, r = divmod(x, p)

            if r == 0:
                prime_factorisation.update([p])
                x = q
                test_up_to_inclusive = math.isqrt(x)
                continue  # Repeat without incrementing i
                          # until there are no more factors
                          # of p in x
                

            if p > test_up_to_inclusive:
                # All prime factors have been divided out up to 
                # some prime p**2 > x.  Therefore x is 1 or prime.

                if x != 1: 
                    prime_factorisation.update([x])

                    # This can break the "all primes known structure"
                    # and means an insertion point needs to be found with
                    # bisect to preserve the sorted order.  By not 
                    # storing sporadic primes, we can use a simple
                    # append in the sieve.
                    # if x not in self.primes:
                    #     # Need to insert sorted, in case of sporadics.
                    #     self.primes.append(x)
                break

            i += 1

            if self.all_primes_known_up_to_inclusive > test_up_to_inclusive:
                continue  # We already know all the primes needed
                          # to factor x

            self.sieve_multiples_of(p, test_up_to_inclusive)




        check = 1

        for prime, exponent in prime_factorisation.items():
            check *= prime**exponent

        assert check == start_x

        with self.cache_file.open('w+t') as f: 
            try:
                cached_primes = json.load(f)['primes']
            except:
                cached_primes = []
            all_primes = {p 
                          for p in self.primes 
                          if p <= self.all_primes_known_up_to_inclusive
                         } 
            all_primes.update(
                          p 
                          for p in self.primes + cached_primes
                          if p > self.all_primes_known_up_to_inclusive
                         )
    
            cache = dict(
                all_primes_known_up_to_inclusive = self.all_primes_known_up_to_inclusive,
                primes = sorted(all_primes),       
                )

            json.dump(cache, f, separators=(',\n', ': ')) 



        return prime_factorisation


    def sieve_multiples_of(self, p: int, test_up_to_inclusive: int) -> None:
        # Sieve out multiples of p, an odd prime.  
        # p**2 is the lowest composite number that cannot
        # already have been sieved out as a factor of 
        # 2, 3, ..., p-1
        # Requires self.primes to contain at least 2 and 3 
        # so that self.primes[-1] is odd.

        sieve_up_to_inclusive = max(test_up_to_inclusive, 
                                    next((p**2 
                                          for p in self.primes
                                          if p**2 >= test_up_to_inclusive
                                         ),
                                         0
                                        )
                                   )


        start = self.all_primes_known_up_to_inclusive + 2
        # print(f'Sieving {p} up to {sieve_up_to_inclusive}')

        composite_start = start - (start % 2*p) - p

        for composite in range(max(p**2, composite_start), sieve_up_to_inclusive + 1, 2*p):
            # print(f'Adding {composite=}')
            # self.composites.add(composite)
            self.composites[composite] = None

        if start < p**2:
            # print(f'searching for new primes from: {start}')
            for candidate in range(start, p**2, 2):
                if candidate not in self.composites:
                    # print(f'''New prime: {candidate} found! 
                    #         ({p=}, bound: {test_up_to_inclusive} )'''.replace('  ','')
                    #      )
                    self.primes.append(candidate)

        if p**2 > self.all_primes_known_up_to_inclusive:
            # print(f'Updating to primes known bounds to {p**2}')
            self.all_primes_known_up_to_inclusive = p**2


if __name__ == '__main__':
    ef = ErathosthenesFactoriser()
    # for prime in ef.primes_from_factoring(start_x):

    if len(sys.argv) >= 2:
        start_x = math.prod(int(arg) for arg in sys.argv[1:])
    else:
        start_x = 100_000

    prime_factorisation = ef.factorise(start_x)

    print(f'\nPrime factorisation of {start_x}: ' + 
          '*'.join(f'({prime}**{power})' if power >= 2 else f'{prime}'
                   for prime, power in prime_factorisation.items()
                  )
         )

    # print(f'Primes: {ef.primes}')
    # print(f'Composites: {list(ef.composites)}')