#include "testlib.h"

int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int q = inf.readInt(1, 200000, "Q");
	inf.readEoln();
	long long total = 0;
	for(int i = 0; i < q; ++i) {
		int op = inf.readInt(1, 3, "opt");
		inf.readSpace();
		if(op == 1) {
			int x = inf.readInt(1, 100000, "x");
			inf.readSpace();
			inf.readInt(-100000000, 100000000, "y");
			total += x;
		} else {
			long long k = inf.readLong(1, 20000000000LL, "k");
			ensuref(k <= total,
					"record %d requests %lld voters but only %lld arrived",
					i + 1, k, total);
		}
		inf.readEoln();
	}
	inf.readEof();
}
