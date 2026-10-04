#include "testlib.h"
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	int e = ans.readInt(-1, 3, "answer");
	int a = ouf.readInt(-1, 3, "answer");
	ans.readEoln();
	ouf.readEoln();
	ans.readEof();
	ouf.readEof();
	if(a != e) quitf(_wa, "expected %d, found %d", e, a);
	quitf(_ok, "accepted");
}
