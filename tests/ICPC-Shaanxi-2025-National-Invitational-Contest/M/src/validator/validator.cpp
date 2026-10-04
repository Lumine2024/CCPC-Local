#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	registerValidation(argc, argv);
	int n = inf.readInt(4, 200000, "n");
	inf.readEoln();
	vector<int> dsu(n + 1), sz(n + 1, 1), degree(n + 1);
	iota(dsu.begin(), dsu.end(), 0);
	auto find = [&](int x) {
		while(dsu[x] != x) x = dsu[x] = dsu[dsu[x]];
		return x;
	};
	for(int i = 1; i < n; i++) {
		int u = inf.readInt(1, n, "x");
		inf.readSpace();
		int v = inf.readInt(1, n, "y");
		inf.readEoln();
		ensuref(u != v, "loop is not a tree edge");
		int a = find(u), b = find(v);
		ensuref(a != b, "edges contain a cycle");
		if(sz[a] < sz[b]) swap(a, b);
		dsu[b] = a;
		sz[a] += sz[b];
		degree[u]++;
		degree[v]++;
	}
	ensuref(*max_element(degree.begin() + 1, degree.end()) >= 3,
			"at least one capital required");
	int q = inf.readInt(1, 200000, "q");
	inf.readEoln();
	for(int i = 0; i < q; i++) {
		inf.readInt(1, n, "u");
		inf.readSpace();
		inf.readInt(1, n, "v");
		inf.readEoln();
	}
	inf.readEof();
}
