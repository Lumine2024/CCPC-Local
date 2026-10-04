import sys

P = 998244353
words = list(map(int, sys.stdin.buffer.read().split()))
n = words[0]
a = words[1:]
inv = [0] * (2 * max(a))
inv[1] = 1
for i in range(2, len(inv)):
    inv[i] = P - (P // i) * inv[P % i] % P

def choose3(x):
    return x * (x - 1) * (x - 2) // 6

def contribution(A, B):
    t = min(A, B)
    s = choose3(B + 1) - choose3(B - t + 1)
    base = B * (B - 1) // 2
    return (s + (B - 1) * base) * inv[A + B - 1] % P

print(*((contribution(a[i], a[i - 1]) +
         contribution(a[i], a[(i + 1) % n])) % P for i in range(n)))
