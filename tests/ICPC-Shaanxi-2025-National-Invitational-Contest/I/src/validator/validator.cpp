#include "testlib.h"
#include <bits/stdc++.h>
using namespace std;
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int t = inf.readInt(1, 100000, "T");
	inf.readEoln();
	for(int i = 0; i < t; i++) {
		inf.readLong(1, 1000000000LL, "n");
		inf.readSpace();
		string p = inf.readToken("[NEWS]{4}", "P");
		inf.readEoln();
		sort(p.begin(), p.end());
		ensuref(p == "ENSW", "P must be a permutation of NEWS");
	}
	inf.readEof();
}
