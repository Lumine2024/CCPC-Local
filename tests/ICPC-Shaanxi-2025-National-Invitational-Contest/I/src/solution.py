import sys

def solve(n, p):
    directions = {'N': (0, 1), 'E': (1, 0), 'W': (-1, 0), 'S': (0, -1)}
    seen = {(0, 0)}
    x = y = 0
    positions = [(0, 0)]
    for i in range(12):
        dx, dy = directions[p[i % 4]]
        while True:
            x += dx
            y += dy
            if (x, y) not in seen:
                break
        seen.add((x, y))
        positions.append((x, y))
    if n <= 12:
        return sum(positions[n])
    q, r = divmod(n, 4)
    return sum(positions[4 + r]) + (q - 1) * (sum(positions[8 + r]) - sum(positions[4 + r]))

it = iter(sys.stdin.buffer.read().split())
t = int(next(it))
out = []
for _ in range(t):
    out.append(str(solve(int(next(it)), next(it).decode())))
sys.stdout.write('\n'.join(out) + '\n')
