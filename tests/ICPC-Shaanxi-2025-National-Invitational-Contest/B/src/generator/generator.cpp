#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	if(argc != 3) return 1;
	string type = argv[1];
	unsigned long long seed = stoull(argv[2]);
	mt19937_64 rng(seed);
	auto ri = [&](int lo, int hi) {
		return lo + int(rng() % (unsigned long long)(hi - lo + 1));
	};
	if(type == "sample") {
		cout << "4\n2 3 4 6\n";
		return 0;
	}
	if(type == "min") {
		cout << "1\n1\n";
		return 0;
	}
	if(type == "distributed") {
		cout << "3\n6 10 15\n";
		return 0;
	}
	if(type == "single-duplicate") {
		cout << "2\n" << (seed % 2 ? "7 7" : "1 1") << "\n";
		return 0;
	}
	int n = type == "random-small" ? ri(3, 60) : 200000;
	cout << n << '\n';
	static const int primes[] = {2,	 3,	 5,	 7,	 11, 13, 17, 19, 23,
								 29, 31, 37, 41, 43, 47, 53, 59, 61,
								 67, 71, 73, 79, 83, 89, 97};
	for(int i = 0; i < n; i++) {
		int x = 1;
		if(type == "all-ones") x = 1;
		else if(type == "powers") x = 1 << ri(0, 19);
		else if(type == "cycling") x = primes[i % 25] * primes[(i + 1) % 25];
		else if(type == "divisibility")
			x = (i % 3 == 0 ? 6 : (i % 3 == 1 ? 12 : 18));
		else if(type == "distinct-prime") x = primes[i % 25];
		else if(type == "random-small") x = ri(1, 100);
		else if(type == "random-large") x = ri(1, 1000000);
		else if(type == "almost-unique") x = 999983 - (i % 1000);
		else x = ri(1, 1000000);
		if(i) cout << ' ';
		cout << x;
	}
	cout << '\n';
}
