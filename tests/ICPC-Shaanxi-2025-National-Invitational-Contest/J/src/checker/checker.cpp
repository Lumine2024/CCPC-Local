#include "testlib.h"
#include <string>
int main(int argc, char *argv[]) {
	registerTestlibCmd(argc, argv);
	int t = inf.readInt();
	inf.readEoln();
	for(int i = 0; i < t; i++) {
		std::string e = ans.readToken();
		std::string a = ouf.readToken();
		ans.readEoln();
		ouf.readEoln();
		if(a != "Yes" && a != "No")
			quitf(_wa, "case %d: expected Yes or No", i + 1);
		if(a != e)
			quitf(_wa, "case %d: expected %s, found %s", i + 1, e.c_str(),
				  a.c_str());
	}
	ans.readEof();
	ouf.readEof();
	quitf(_ok, "%d cases", t);
}
