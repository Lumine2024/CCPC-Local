import heapq
import sys
def main():
    data=list(map(int,sys.stdin.buffer.read().split()))
    at=0;n=data[at];at+=1
    graph=[[] for _ in range(n+1)]
    for _ in range(n-1):
        u,v=data[at:at+2];at+=2
        graph[u].append(v);graph[v].append(u)
    inf=10**9
    best=[(inf,inf)]*(n+1)
    heap=[]
    for v in range(1,n+1):
        if len(graph[v])>2:
            best[v]=(0,v);heapq.heappush(heap,(0,v,v))
    while heap:
        d,c,v=heapq.heappop(heap)
        if best[v]!=(d,c):continue
        for w in graph[v]:
            candidate=(d+1,c)
            if candidate<best[w]:
                best[w]=candidate;heapq.heappush(heap,(d+1,c,w))
    parent=[0]*(n+1);depth=[0]*(n+1);prefix=[0]*(n+1);order=[1]
    for v in order:
        for w in graph[v]:
            if w!=parent[v]:
                parent[w]=v;depth[w]=depth[v]+1
                prefix[w]=prefix[v]+(best[w][1]!=best[v][1])
                order.append(w)
    q=data[at];at+=1;out=[]
    for _ in range(q):
        u,v=data[at:at+2];at+=2
        a,b=u,v
        while depth[a]>depth[b]:a=parent[a]
        while depth[b]>depth[a]:b=parent[b]
        while a!=b:a=parent[a];b=parent[b]
        out.append(str(prefix[u]+prefix[v]-2*prefix[a]+1))
    sys.stdout.write("\n".join(out)+"\n")
if __name__=="__main__":main()
