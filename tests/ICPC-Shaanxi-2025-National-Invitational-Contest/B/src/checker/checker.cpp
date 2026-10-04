#include "testlib.h"
int main(int argc, char **argv) {
	registerTestlibCmd(argc, argv);
	long long expected = ans.readLong(0, 20000100000LL, "answer");
	long long actual = ouf.readLong(0, 20000100000LL, "answer");
	if(actual != expected)
		quitf(_wa, "expected %lld, found %lld", expected, actual);
	ans.seekEof();
	ans.readEof();
	ouf.seekEof();
	ouf.readEof();
	quitf(_ok, "answer %lld", actual);
}
