#include "testlib.h"
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(1, 3, "n");
	inf.readEoln();
	for(int i = 0; i < n; i++) {
		inf.readInt(1, 200000, "a_i");
		if(i + 1 < n) inf.readSpace();
		else inf.readEoln();
	}
	int m = inf.readInt(1, 100, "m");
	inf.readEoln();
	for(int i = 0; i < m; i++) {
		inf.readInt(1, 2, "t_i");
		inf.readSpace();
		inf.readLong(1, 1000000000LL, "x_i");
		inf.readEoln();
	}
	inf.readEof();
}
