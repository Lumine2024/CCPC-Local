import math
import sys

n, m, s = sys.stdin.read().split()
n, m = int(n), int(m)
d = math.gcd(n, m)
count = [[0, 0] for _ in range(d)]
for i, ch in enumerate(s):
    count[i % d][int(ch)] += 1
print(m * sum(max(pair) for pair in count))
