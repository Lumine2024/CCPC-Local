#include "testlib.h"

int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	const int n = inf.readInt(1, 1000, "n");
	inf.readSpace();
	inf.readInt(1, 10000, "m");
	inf.readEoln();
	for(int i = 0; i < n; ++i) {
		inf.readInt(0, 100000, "a_i");
		if(i + 1 == n) inf.readEoln();
		else inf.readSpace();
	}
	inf.readEof();
}
