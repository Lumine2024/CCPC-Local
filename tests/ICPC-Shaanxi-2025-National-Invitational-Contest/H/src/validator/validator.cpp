#include "testlib.h"
#include <string>
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 100000, "N");
	inf.readSpace();
	int q = inf.readInt(1, 100000, "Q");
	inf.readEoln();
	std::string s = inf.readToken("[a-e]+", "S");
	inf.readEoln();
	ensuref((int)s.size() == n, "S must have length N");
	for(int i = 1; i <= q; i++) {
		int l = inf.readInt(1, n, "l");
		inf.readSpace();
		int r = inf.readInt(1, n, "r");
		inf.readSpace();
		inf.readInt(1, 1000000000, "k");
		inf.readEoln();
		ensuref(l <= r, "query %d has l > r", i);
	}
	inf.readEof();
}
