#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 14, "n");
	inf.readSpace();
	int m = inf.readInt(1, 80000, "m");
	inf.readSpace();
	inf.readInt(1, 20, "k");
	inf.readEoln();
	int N = 1 << n;
	vector<vector<int>> out(N);
	vector<int> indeg(N);
	for(int i = 0; i < m; i++) {
		int u = inf.readInt(0, N - 1, "u");
		inf.readSpace();
		int v = inf.readInt(0, N - 1, "v");
		inf.readEoln();
		ensuref(u != v, "self loop at edge %d", i + 1);
		out[u].push_back(v);
		indeg[v]++;
	}
	inf.readEof();
	queue<int> q;
	for(int v = 0; v < N; v++)
		if(!indeg[v]) q.push(v);
	int seen = 0;
	while(!q.empty()) {
		int u = q.front();
		q.pop();
		seen++;
		for(int v : out[u])
			if(--indeg[v] == 0) q.push(v);
	}
	ensuref(seen == N, "graph contains a directed cycle");
}
