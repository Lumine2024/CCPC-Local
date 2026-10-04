#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char *argv[]) {
	registerGen(argc, argv, 1);
	if(argc != 3) return 1;
	string type = argv[1];
	rnd.setSeed(atoll(argv[2]));
	int n = 1, m = 1;
	string s;
	if(type == "sample-1") {
		n = 3;
		m = 4;
		s = "111";
	} else if(type == "sample-2") {
		n = 3;
		m = 2;
		s = "101";
	} else if(type == "min") {
		n = m = 1;
		s = rnd.next(0, 1) ? "1" : "0";
	} else if(type == "divisible") {
		n = rnd.next(2, 100000);
		m = n;
		s.resize(n);
		for(int i = 0; i < n; i++) s[i] = (i & 1) ? '0' : '1';
	} else if(type == "coprime") {
		n = 99991;
		m = 100000;
		s.resize(n);
		for(char &c : s) c = rnd.next(0, 1) ? '1' : '0';
	} else if(type == "skew") {
		n = 100000;
		m = 50000;
		s.resize(n);
		for(int i = 0; i < n; i++) s[i] = (i < 50000) ? '0' : '1';
	} else if(type == "all-one") {
		n = m = 100000;
		s = string(n, '1');
	} else if(type == "all-zero") {
		n = m = 100000;
		s = string(n, '0');
	} else if(type == "large") {
		n = rnd.next(90000, 100000);
		m = rnd.next(90000, 100000);
		s.resize(n);
		for(char &c : s) c = rnd.next(0, 1) ? '1' : '0';
	} else if(type == "small") {
		n = rnd.next(1, 30);
		m = rnd.next(1, 30);
		s.resize(n);
		for(char &c : s) c = rnd.next(0, 1) ? '1' : '0';
	} else return 2;
	cout << n << ' ' << m << '\n' << s << '\n';
}
