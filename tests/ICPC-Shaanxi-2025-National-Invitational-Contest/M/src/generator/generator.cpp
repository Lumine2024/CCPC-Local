#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	if(argc != 3) return 1;
	string type = argv[1];
	uint64_t seed = stoull(argv[2]);
	mt19937_64 rng(seed);
	if(type == "sample") {
		cout << "7\n1 2\n1 3\n1 7\n3 4\n4 5\n4 6\n4\n1 4\n2 6\n5 5\n2 3\n";
		return 0;
	}
	if(type == "min") {
		cout << "4\n1 2\n1 3\n1 4\n5\n1 1\n2 3\n2 4\n3 4\n1 2\n";
		return 0;
	}
	if(type == "tie") {
		cout << "9\n1 2\n2 3\n3 4\n4 5\n5 6\n2 7\n6 8\n6 9\n7\n4 4\n2 4\n4 "
				"6\n3 5\n1 9\n7 8\n5 5\n";
		return 0;
	}
	int n = type == "random-small" ? 10 + int(rng() % 90) : 200000;
	vector<pair<int, int>> e;
	e.reserve(n - 1);
	if(type == "star-large") {
		for(int v = 2; v <= n; v++) e.push_back({1, v});
	} else if(type == "chain-one-capital") {
		for(int v = 2; v <= n - 2; v++) e.push_back({v - 1, v});
		e.push_back({n - 2, n - 1});
		e.push_back({n - 2, n});
	} else if(type == "two-capitals") {
		for(int v = 2; v <= n - 2; v++) e.push_back({v - 1, v});
		e.push_back({2, n - 1});
		e.push_back({n - 2, n});
	} else if(type == "binary-large") {
		for(int v = 2; v <= n; v++) e.push_back({v / 2, v});
	} else {
		for(int v = 2; v <= n; v++) {
			int p = 1 + int(rng() % (v - 1));
			e.push_back({p, v});
		}
		vector<int> d(n + 1);
		for(auto [u, v] : e) d[u]++, d[v]++;
		if(*max_element(d.begin() + 1, d.end()) < 3) {
			int old = e.back().first;
			for(int x = 1; x < n; x++)
				if(x != old && d[x] == 2) {
					e.back() = {x, n};
					break;
				}
		}
	}
	int q = type == "random-small" ? 100 : 200000;
	cout << n << '\n';
	for(auto [u, v] : e) cout << u << ' ' << v << '\n';
	cout << q << '\n';
	for(int i = 0; i < q; i++) {
		int u = 1 + int(rng() % n), v = 1 + int(rng() % n);
		if(i % 11 == 0) v = u;
		if(type == "two-capitals" && i % 7 == 0) u = 2, v = n - 2;
		cout << u << ' ' << v << '\n';
	}
}
