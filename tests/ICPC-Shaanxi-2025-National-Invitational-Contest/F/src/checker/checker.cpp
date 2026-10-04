#include "testlib.h"
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	int n = inf.readInt();
	for(int i = 0; i < n; i++) {
		long long expected = ans.readLong(0LL, 998244352LL);
		long long actual = ouf.readLong(0LL, 998244352LL);
		if(actual != expected)
			quitf(_wa, "position %d: expected %lld, found %lld", i + 1,
				  expected, actual);
	}
	ans.readEoln();
	ans.readEof();
	ouf.readEoln();
	ouf.readEof();
	quitf(_ok, "accepted");
}
