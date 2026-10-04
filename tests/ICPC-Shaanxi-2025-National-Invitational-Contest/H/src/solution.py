"""Direct per-query reference for the small test group."""

import sys

CAP = 1_000_000_001
MASK = (1 << 32) - 1


def answer(s: str, left: int, right: int, rank: int) -> int:
    left -= 1
    right -= 1
    if left == right:
        return -1
    nxt = [[right] * 5 for _ in range(right + 1)]
    ways = [0] * (right + 1)
    ways[right] = 1
    for p in range(right - 1, left, -1):
        nxt[p] = nxt[p + 1].copy()
        nxt[p][ord(s[p]) - 97] = p
        ways[p] = min(CAP, 1 + sum(ways[nxt[p][c] + 1] for c in range(5) if nxt[p][c] < right))
    tail = ord(s[right]) - 97
    p = left + 1
    h = ord(s[left]) - 96
    while True:
        for c in range(5):
            count = (c == tail) + (ways[nxt[p][c] + 1] if nxt[p][c] < right else 0)
            if rank > count:
                rank -= count
                continue
            if c == tail:
                if rank == 1:
                    return (h * 1331 + c + 1) & MASK
                rank -= 1
            h = (h * 1331 + c + 1) & MASK
            p = nxt[p][c] + 1
            break
        else:
            return -1


def main() -> None:
    tokens = sys.stdin.buffer.read().split()
    n, q = map(int, tokens[:2])
    s = tokens[2].decode()
    assert len(s) == n
    out = []
    at = 3
    for _ in range(q):
        left, right, rank = map(int, tokens[at : at + 3])
        out.append(str(answer(s, left, right, rank)))
        at += 3
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
