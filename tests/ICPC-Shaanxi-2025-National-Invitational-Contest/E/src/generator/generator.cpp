#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char *argv[]) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 1;
	string type = argv[1];
	rnd.setSeed(atoll(argv[2]));
	int n = 2, k = 2;
	vector<pair<int, int>> e;
	if(type == "sample-1") e = {{1, 0}, {3, 2}};
	else if(type == "sample-2") e = {{3, 1}, {2, 0}};
	else if(type == "sample-3") {
		n = 3;
		k = 3;
		e = {{7, 3}, {6, 2}, {5, 1}, {4, 0}, {7, 5}, {6, 4}};
	} else if(type == "single") {
		n = 1;
		k = rnd.next(1, 20);
		e = {{0, 1}};
	} else if(type == "small") {
		n = rnd.next(2, 5);
		k = rnd.next(1, 5);
		int N = 1 << n;
		vector<pair<int, int>> poss;
		for(int u = 0; u < N; u++)
			for(int v = u + 1; v < N; v++) poss.push_back({u, v});
		std::shuffle(poss.begin(), poss.end(),
					 std::mt19937((unsigned)atoll(argv[2])));
		int m = rnd.next(1, min(40, (int)poss.size()));
		e.assign(poss.begin(), poss.begin() + m);
	} else if(type == "chain") {
		n = 14;
		k = 20;
		for(int u = 0; u < (1 << n) - 1; u++) e.push_back({u, u + 1});
	} else if(type == "mex") {
		n = 14;
		k = 20;
		for(int u = 1; u < 400; u++)
			for(int v = 0; v < u; v++) e.push_back({u, v});
	} else if(type == "random-large" || type == "layered") {
		n = 14;
		k = 20;
		int N = 1 << n;
		unordered_set<long long> used;
		while((int)e.size() < 80000) {
			int u, v;
			if(type == "layered") {
				u = rnd.next(0, N / 2 - 1);
				v = rnd.next(N / 2, N - 1);
			} else {
				u = rnd.next(0, N - 2);
				v = rnd.next(u + 1, N - 1);
			}
			long long key = 1LL * u * N + v;
			if(used.insert(key).second) e.push_back({u, v});
		}
	} else return 2;
	cout << n << ' ' << e.size() << ' ' << k << '\n';
	for(auto [u, v] : e) cout << u << ' ' << v << '\n';
}
