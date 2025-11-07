import sys
import string

assert 5 == string.ascii_lowercase.index('f')

for word in sys.argv[1:]:
    print(''.join(str(string.ascii_lowercase.index(c)).zfill(2) 
                  for c in word.lower()
                 )
         )