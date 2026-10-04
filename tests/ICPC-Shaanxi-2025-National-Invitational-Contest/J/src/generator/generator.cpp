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
		cout << "3\n3\n2 3 2\n4\n2 2 2 2\n6\n3 2 3 2 3 3\n";
		return 0;
	}
	int t;
	if(type == "tiny") t = 2000;
	else if(type == "large") t = 10;
	else if(type == "many") t = 100000;
	else if(type == "all-two" || type == "all-three" || type == "mixed") t = 10;
	else return 2;
	cout << t << '\n';
	for(int j = 0; j < t; j++) {
		int n;
		if(type == "tiny") n = rnd.next(1, 25);
		else if(type == "large") n = 100000;
		else if(type == "many") n = 10;
		else n = 99970 + j;
		int k;
		if(type == "all-two") k = 0;
		else if(type == "all-three") k = n;
		else if(type == "mixed") k = 1 + (j * 7 + seed) % (n - 1);
		else k = rnd.next(0, n);
		vector<int> a(n, 2);
		for(int i = 0; i < k; i++) a[i] = 3;
		if(type == "tiny" || type == "large" || type == "many")
			shuffle(a.begin(), a.end(), mt19937(seed * 1000003u + j));
		cout << n << '\n';
		for(int i = 0; i < n; i++) cout << a[i] << (i + 1 == n ? '\n' : ' ');
	}
}
