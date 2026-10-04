#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char *argv[]) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 1;
	string type = argv[1];
	rnd.setSeed(atoll(argv[2]));
	vector<int> a;
	if(type == "sample") a = {1, 1, 2};
	else if(type == "min") a = {1, 1, 1};
	else if(type == "one-high") a = {1, 100000, 1};
	else if(type == "high-one") a = {100000, 1, 100000};
	else if(type == "small") {
		int n = rnd.next(3, 30);
		a.resize(n);
		for(int &x : a) x = rnd.next(1, 8);
	} else if(type == "ones") {
		int n = rnd.next(90000, 100000);
		a.assign(n, 1);
		a[rnd.next(0, n - 1)] = 100000;
	} else if(type == "alternating") {
		int n = 100000;
		a.resize(n);
		for(int i = 0; i < n; i++) a[i] = (i & 1) ? 100000 : 1;
	} else if(type == "equal-high") {
		a.assign(100000, 100000);
	} else if(type == "max-random") {
		int n = 100000;
		a.resize(n);
		for(int &x : a) x = rnd.next(1, 100000);
	} else if(type == "near-max") {
		int n = 100000;
		a.resize(n);
		for(int &x : a) x = rnd.next(90000, 100000);
	} else return 2;
	cout << a.size() << '\n';
	for(int i = 0; i < (int)a.size(); i++)
		cout << a[i] << (i + 1 == (int)a.size() ? '\n' : ' ');
}
