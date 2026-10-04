#include "testlib.h"
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	long long e = ans.readLong(-1LL, 200000000LL, "answer");
	long long a = ouf.readLong(-1LL, 200000000LL, "answer");
	ans.readEoln();
	ouf.readEoln();
	ans.readEof();
	ouf.readEof();
	if(a != e) quitf(_wa, "expected %lld, found %lld", e, a);
	quitf(_ok, "accepted");
}
