#include "testlib.h"
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int t = inf.readInt(1, 100000, "T");
	inf.readEoln();
	int total = 0;
	for(int c = 0; c < t; c++) {
		int n = inf.readInt(1, 100000, "n");
		inf.readEoln();
		total += n;
		ensuref(total <= 1000000, "sum n exceeds 1e6");
		for(int i = 0; i < n; i++) {
			inf.readInt(2, 3, "a_i");
			if(i + 1 < n) inf.readSpace();
			else inf.readEoln();
		}
	}
	inf.readEof();
}
