#include "testlib.h"
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 500000, "n");
	inf.readSpace();
	int m = inf.readInt(0, 500000, "m");
	inf.readEoln();
	for(int i = 0; i < m; i++) {
		int u = inf.readInt(1, n, "u");
		inf.readSpace();
		int v = inf.readInt(1, n, "v");
		ensuref(u != v, "self-loop at edge %d", i + 1);
		inf.readSpace();
		inf.readInt(1, 100000000, "length");
		inf.readEoln();
	}
	inf.readEof();
}
