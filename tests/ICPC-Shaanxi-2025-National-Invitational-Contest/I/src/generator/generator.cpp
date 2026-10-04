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
		cout << "6\n9 NEWS\n9 NESW\n9 NSEW\n1000000000 SEWN\n1000000000 "
				"SWNE\n1000000000 SNWE\n";
		return 0;
	}
	string p = "ENSW";
	vector<string> ps;
	do {
		ps.push_back(p);
	} while(next_permutation(p.begin(), p.end()));
	int t = (type == "large" || type == "maximum")
				? 100000
				: (type == "small" ? 10000 : 96);
	if(type != "large" && type != "maximum" && type != "small" &&
	   type != "boundary")
		return 2;
	cout << t << '\n';
	for(int i = 0; i < t; i++) {
		long long n;
		if(type == "boundary") n = 1 + i % 16;
		else if(type == "small") n = rnd.next(1, 200);
		else if(type == "large") n = rnd.next(1LL, 1000000000LL);
		else n = 1000000000LL - i % 8;
		cout << n << ' ' << ps[(i + seed) % 24] << '\n';
	}
}
