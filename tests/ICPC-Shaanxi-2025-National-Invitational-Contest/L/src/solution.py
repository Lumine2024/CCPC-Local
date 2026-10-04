import sys
v=list(map(int,sys.stdin.buffer.read().split()))
it=iter(v)
n=next(it)
a=[next(it) for _ in range(n)]
m=next(it)
days=[(next(it),next(it)) for _ in range(m)]
answer=n+1
for bag in range(1,1<<n):
    if all(any((t==1 and sum(a[i] for i in range(n) if outfit>>i&1)>=x) or
               (t==2 and sum(a[i] for i in range(n) if outfit>>i&1)<=x)
               for outfit in range(1,1<<n) if outfit&bag==outfit)
           for t,x in days):
        answer=min(answer,bag.bit_count())
print(-1 if answer==n+1 else answer)
