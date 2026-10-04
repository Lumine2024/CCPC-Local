#include "testlib.h"
#include <string>
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	std::string expected = ans.readToken("(First|Second)");
	ans.readEoln();
	ans.readEof();
	std::string actual = ouf.readToken("(First|Second)");
	ouf.readEoln();
	ouf.readEof();
	if(expected != actual)
		quitf(_wa, "expected %s, found %s", expected.c_str(), actual.c_str());
	quitf(_ok, "accepted");
}
