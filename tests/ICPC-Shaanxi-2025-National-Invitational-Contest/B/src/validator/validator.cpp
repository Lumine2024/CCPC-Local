#include "testlib.h"
int main(int argc, char **argv) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 200000, "n");
	inf.readEoln();
	for(int i = 0; i < n; i++) {
		if(i) inf.readSpace();
		inf.readInt(1, 1000000, "a");
	}
	inf.readEoln();
	inf.readEof();
}
