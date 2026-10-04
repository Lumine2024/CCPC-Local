#include "testlib.h"
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	int t = inf.readInt();
	inf.readEoln();
	for(int i = 0; i < t; i++) {
		long long e = ans.readLong();
		ans.readEoln();
		long long a =
			ouf.readLong(-2000000000LL, 2000000000LL, "coordinate sum");
		ouf.readEoln();
		if(a != e)
			quitf(_wa, "case %d: expected %lld, found %lld", i + 1, e, a);
	}
	ans.readEof();
	ouf.readEof();
	quitf(_ok, "%d cases", t);
}
