#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 2;
	string type = argv[1];
	int seed = atoi(argv[2]);
	rnd.setSeed(seed);
	int n = 3, m = 100;
	vector<int> a(3);
	vector<pair<int, long long>> d;
	if(type == "sample") {
		n = 3;
		m = 1;
		a = {2, 3, 5};
		d = {{1, 10}};
	} else if(type == "sample-2") {
		n = 3;
		m = 2;
		a = {2, 3, 5};
		d = {{1, 5}, {2, 2}};
	} else if(type == "sample-3") {
		n = 3;
		m = 2;
		a = {7, 11, 13};
		d = {{1, 24}, {2, 7}};
	} else if(type == "sample-4") {
		n = 2;
		m = 2;
		a = {17, 19};
		d = {{1, 16}, {2, 18}};
	} else if(type == "sample-5") {
		n = 3;
		m = 2;
		a = {2, 11, 19};
		d = {{1, 1000000000LL}, {2, 1}};
	} else if(type == "single") {
		n = 1;
		m = 1;
		a = {seed % 200000 + 1};
		d = {{seed % 2 + 1, seed % 3 == 0 ? 1000000000LL : (long long)a[0]}};
	} else if(type == "anti-upper") {
		n = 3;
		m = 2;
		a = {1, 100000, 200000};
		d = {{1, 100000}, {2, 1}};
	} else if(type == "mixed" || type == "random" || type == "extreme") {
		if(type == "mixed") a = {1, 100000, 200000};
		else
			for(int &i : a) i = rnd.next(1, 200000);
		for(int i = 0; i < m; i++) {
			int t = (type == "mixed" ? i % 2 + 1 : rnd.next(1, 2));
			long long x =
				type == "extreme"
					? (i % 3 == 0 ? 1000000000LL : rnd.next(1LL, 600000LL))
					: rnd.next(1LL, 600000LL);
			d.push_back({t, x});
		}
	} else return 2;
	cout << n << '\n';
	for(int i = 0; i < n; i++) cout << a[i] << (i + 1 == n ? '\n' : ' ');
	cout << m << '\n';
	for(auto [t, x] : d) cout << t << ' ' << x << '\n';
}
