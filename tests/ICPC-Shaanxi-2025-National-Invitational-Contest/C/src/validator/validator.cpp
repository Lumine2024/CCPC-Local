#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	registerValidation(argc, argv);
	int n = inf.readInt(2, 500000, "n");
	inf.readSpace();
	int m = inf.readInt(0, 1000000, "m");
	inf.readEoln();
	vector<pair<int, int>> e;
	e.reserve(1000000);
	auto readEdge = [&]() {
		int u = inf.readInt(1, n, "u");
		inf.readSpace();
		int v = inf.readInt(1, n, "v");
		ensuref(u < v, "endpoints must be in increasing order");
		inf.readEoln();
		e.push_back({u, v});
	};
	for(int i = 0; i < m; i++) readEdge();
	int q = inf.readInt(0, 1000000, "q");
	inf.readEoln();
	ensuref((long long)m + q <= 1000000,
			"too many total wires for the stated dimensions");
	for(int i = 0; i < q; i++) readEdge();
	inf.readEof();
	sort(e.begin(), e.end(), [](auto a, auto b) {
		if(a.first != b.first) return a.first < b.first;
		return a.second > b.second;
	});
	vector<pair<int, int>> stk;
	stk.reserve(e.size());
	for(size_t i = 0; i < e.size(); i++) {
		auto [u, v] = e[i];
		if(i && e[i] == e[i - 1]) ensuref(false, "duplicate wire");
		while(!stk.empty() && stk.back().second <= u) stk.pop_back();
		ensuref(stk.empty() || v <= stk.back().second, "crossing wires");
		stk.push_back({u, v});
	}
}
