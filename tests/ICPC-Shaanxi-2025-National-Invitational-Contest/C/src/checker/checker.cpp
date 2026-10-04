#include "testlib.h"
int main(int argc, char **argv) {
	registerTestlibCmd(argc, argv);
	int count = 0;
	while(!ans.seekEof()) {
		long long a = ans.readLong(0, 1000000000000000000LL, "expected");
		long long b = ouf.readLong(0, 1000000000000000000LL, "actual");
		if(a != b)
			quitf(_wa, "line %d: expected %lld, found %lld", count + 1, a, b);
		count++;
	}
	ans.readEof();
	ouf.seekEof();
	ouf.readEof();
	quitf(_ok, "%d answers", count);
}
