#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;

int main(int argc, char *argv[]) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 1;
	const string type = argv[1];
	rnd.setSeed(atoll(argv[2]));

	int n = 0, m = 0;
	vector<int> a;
	if(type == "sample") {
		n = 4;
		m = 6;
		a = {5, 1, 6, 1};
	} else if(type == "min") {
		n = 1;
		m = 1;
		a = {0};
	} else if(type == "flat") {
		n = 1000;
		m = 10000;
		a.assign(n, 0);
	} else if(type == "single-valley") {
		n = 3;
		m = 10000;
		a = {100000, 0, 100000};
	} else if(type == "nested") {
		n = 999;
		m = 8000 + rnd.next(0, 2000);
		a.resize(n);
		for(int i = 0; i < n; ++i)
			a[i] = (i % 2 == 0) ? 100000 - i / 2 : rnd.next(0, 100);
	} else if(type == "saw") {
		n = 1000;
		m = 10000;
		a.resize(n);
		for(int i = 0; i < n; ++i)
			a[i] = (i % 2 == 0) ? 100000 : rnd.next(0, 20);
	} else if(type == "random-small") {
		n = rnd.next(2, 8);
		m = rnd.next(1, 30);
		a.resize(n);
		for(int &value : a) value = rnd.next(0, 8);
	} else if(type == "random-large") {
		n = rnd.next(850, 1000);
		m = rnd.next(8500, 10000);
		a.resize(n);
		for(int &value : a) value = rnd.next(0, 100000);
	} else if(type == "max") {
		n = 1000;
		m = 10000;
		a.resize(n);
		for(int i = 0; i < n; ++i) a[i] = (i % 3 == 1) ? 0 : 100000;
	} else {
		cerr << "Unknown case type: " << type << '\n';
		return 2;
	}

	cout << n << ' ' << m << '\n';
	for(int i = 0; i < n; ++i) cout << a[i] << (i + 1 == n ? '\n' : ' ');
}
