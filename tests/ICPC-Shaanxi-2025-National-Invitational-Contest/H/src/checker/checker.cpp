#include "testlib.h"
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	inf.readInt();
	int q = inf.readInt();
	for(int i = 1; i <= q; i++) {
		long long expected = ans.readLong(-1LL, 4294967295LL);
		long long actual = ouf.readLong(-1LL, 4294967295LL);
		if(expected != actual)
			quitf(_wa, "query %d: expected %lld, found %lld", i, expected,
				  actual);
	}
	ans.readEoln();
	ans.readEof();
	ouf.readEoln();
	ouf.readEof();
	quitf(_ok, "accepted");
}
