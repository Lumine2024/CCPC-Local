#include "testlib.h"

int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);

	long long expected = ans.readLong(0LL, 1000000006LL, "expected");
	long long actual = ouf.readLong(0LL, 1000000006LL, "actual");
	ans.seekEof();
	ans.readEof();
	ouf.seekEof();
	ouf.readEof();

	if(expected != actual) {
		quitf(_wa, "expected %lld, found %lld", expected, actual);
	}

	quitf(_ok, "accepted");
}
