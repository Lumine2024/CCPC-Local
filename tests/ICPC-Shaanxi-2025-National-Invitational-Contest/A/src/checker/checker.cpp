#include "testlib.h"

int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	int line = 0;
	while(!ans.seekEof()) {
		++line;
		long long expected =
			ans.readLong(0, 2000000000000000000LL, "expected cost");
		long long actual = ouf.readLong(0, 2000000000000000000LL, "cost");
		if(actual != expected)
			quitf(_wa, "line %d: expected %lld, found %lld", line, expected,
				  actual);
	}
	ans.readEof();
	ouf.seekEof();
	ouf.readEof();
	quitf(_ok, "%d answers", line);
}
