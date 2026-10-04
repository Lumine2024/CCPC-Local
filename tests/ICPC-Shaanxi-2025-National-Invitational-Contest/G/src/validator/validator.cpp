#include "testlib.h"
#include <string>
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 100000, "n");
	inf.readSpace();
	inf.readInt(1, 100000, "m");
	inf.readEoln();
	std::string s = inf.readToken("[01]+", "A");
	inf.readEoln();
	ensuref((int)s.size() == n, "A length must equal n");
	inf.readEof();
}
