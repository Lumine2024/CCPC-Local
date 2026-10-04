#include "testlib.h"
int main(int argc, char **argv) {
	registerTestlibCmd(argc, argv);
	int lines = 0;
	while(!ans.seekEof()) {
		int a = ans.readInt(1, 200000, "expected");
		int b = ouf.readInt(1, 200000, "actual");
		if(a != b)
			quitf(_wa, "query %d: expected %d, found %d", lines + 1, a, b);
		++lines;
	}
	ans.readEof();
	ouf.seekEof();
	ouf.readEof();
	quitf(_ok, "%d answers", lines);
}
