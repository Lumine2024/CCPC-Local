#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 2;
	string type = argv[1];
	int seed = atoi(argv[2]);
	rnd.setSeed(seed);
	if(type == "sample") {
		cout << "5 6\n1 5 4\n1 3 4\n4 1 5\n2 1 2\n2 5 4\n1 2 1\n";
		return 0;
	}
	int n = 0, m = 0;
	vector<array<int, 3>> e;
	auto add = [&](int u, int v, int w) {
		if(u != v) e.push_back({u, v, w});
	};
	if(type == "isolated") {
		n = 500000;
	} else if(type == "path") {
		n = 500000;
		for(int i = 1; i < n; i++) add(i, i + 1, (i + seed) % 100000000 + 1);
	} else if(type == "star") {
		n = 500000;
		for(int i = 2; i <= n; i++) add(1, i, (i + seed) % 100000000 + 1);
	} else if(type == "parallel") {
		n = 4;
		add(1, 2, 1);
		add(1, 2, 2);
		add(3, 4, 100000000);
	} else if(type == "odd") {
		n = 5;
		for(int i = 1; i < 5; i++) add(i, i + 1, seed % 100 + 1);
		add(5, 1, seed % 100 + 1);
	} else if(type == "even") {
		n = 6;
		for(int i = 1; i < 6; i++) add(i, i + 1, seed % 100 + 1);
		add(6, 1, seed % 100 + 1);
	} else if(type == "random-small" || type == "random-large") {
		n = type == "random-small" ? rnd.next(2, 100) : 500000;
		int target = type == "random-small" ? rnd.next(1, 300) : 500000;
		while((int)e.size() < target) {
			int u = rnd.next(1, n), v = rnd.next(1, n);
			if(u != v) add(u, v, rnd.next(1, 100000000));
		}
	} else return 2;
	cout << n << ' ' << e.size() << '\n';
	for(auto z : e) cout << z[0] << ' ' << z[1] << ' ' << z[2] << '\n';
}
