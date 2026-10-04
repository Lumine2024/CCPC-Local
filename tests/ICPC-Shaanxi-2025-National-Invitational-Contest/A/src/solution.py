import heapq
import sys


def main():
    data = list(map(int, sys.stdin.buffer.read().split()))
    p = 0
    q = data[p]
    p += 1
    count = {}
    negative_heap = []
    positive_heap = []
    positive = negative = 0
    answer = []

    def add(value, amount):
        if not amount:
            return
        old = count.get(value, 0)
        count[value] = old + amount
        if old == 0 and value < 0:
            heapq.heappush(negative_heap, -value)
        if old == 0 and value > 0:
            heapq.heappush(positive_heap, value)

    for _ in range(q):
        op = data[p]
        p += 1
        if op == 1:
            x, y = data[p:p + 2]
            p += 2
            add(y, x)
            if y > 0:
                positive += x
            elif y < 0:
                negative += x
            continue
        k = data[p]
        p += 1
        need = max(0, k - (positive if op == 2 else negative))
        cost = 0
        while need:
            if count.get(0, 0):
                value = 0
            elif op == 2:
                while negative_heap and count.get(-negative_heap[0], 0) == 0:
                    heapq.heappop(negative_heap)
                value = -negative_heap[0]
            else:
                while positive_heap and count.get(positive_heap[0], 0) == 0:
                    heapq.heappop(positive_heap)
                value = positive_heap[0]
            take = min(need, count[value])
            count[value] -= take
            if op == 2:
                if value < 0:
                    negative -= take
                positive += take
                add(1, take)
                cost += take * (1 - value)
            else:
                if value > 0:
                    positive -= take
                negative += take
                add(-1, take)
                cost += take * (1 + value)
            need -= take
        answer.append(str(cost))
    sys.stdout.write('\n'.join(answer))


if __name__ == '__main__':
    main()
