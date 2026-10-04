#include "testlib.h"
int main(int argc, char *argv[]) {
	registerValidation(argc, argv);
	int n = inf.readInt(3, 100000, "n");
	inf.readEoln();
	for(int i = 0; i < n; i++) {
		inf.readInt(1, 100000, ("a[" + std::to_string(i) + "]").c_str());
		if(i + 1 < n) inf.readSpace();
		else inf.readEoln();
	}
	inf.readEof();
}
