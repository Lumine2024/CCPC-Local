#include <bits/stdc++.h>
using namespace std;
using i64 = long long;

int main(int argc, char **argv) {
	if(argc != 3) return 1;
	string type = argv[1];
	uint64_t seed = stoull(argv[2]);
	mt19937_64 rng(seed);
	auto between = [&](i64 lo, i64 hi) {
		return lo + (i64)(rng() % (uint64_t)(hi - lo + 1));
	};
	if(type == "sample") {
		cout << "6\n1 10 10\n1 10 -10\n1 10 0\n2 30\n3 30\n3 20\n";
		return 0;
	}
	if(type == "min") {
		cout << "2\n1 1 0\n2 1\n";
		return 0;
	}
	if(type == "extreme") {
		cout << "6\n1 100000 -100000000\n1 100000 100000000\n2 200000\n3 "
				"200000\n2 200000\n3 100000\n";
		return 0;
	}
	if(type == "partial") {
		cout << "10\n1 7 -3\n1 4 -1\n1 5 0\n1 3 2\n2 8\n3 12\n2 19\n1 5 0\n3 "
				"23\n2 17\n";
		return 0;
	}
	if(type == "huge-count") {
		int arrivals = 30000 + int(seed % 1000);
		cout << arrivals + 3 << '\n';
		for(int i = 0; i < arrivals; ++i) cout << "1 100000 -100000000\n";
		i64 total = 100000LL * arrivals;
		cout << "2 " << total << '\n'
			 << "3 " << total << '\n'
			 << "2 " << total << '\n';
		return 0;
	}
	if(type == "alternating") {
		int q = 150000;
		cout << q << '\n' << "1 100000 0\n";
		for(int i = 1; i < q; ++i)
			cout << (i & 1 ? "2 100000\n" : "3 100000\n");
		return 0;
	}
	if(type == "many-groups") {
		int groups = 100000;
		cout << groups + 2 << '\n';
		for(int i = 1; i <= groups; ++i) cout << "1 1 " << -i << '\n';
		cout << "2 " << groups << '\n' << "3 " << groups << '\n';
		return 0;
	}
	int q = type == "random-small" ? 1000 : 200000;
	cout << q << '\n';
	i64 total = 0;
	for(int i = 0; i < q; ++i) {
		bool arrive =
			i == 0 || (rng() % 100 < (type == "random-small" ? 55 : 65));
		if(arrive) {
			int x = (int)between(1, type == "random-small" ? 20 : 100000);
			int y;
			if(type == "random-small") y = (int)between(-20, 20);
			else if(rng() % 4 == 0) y = (int)between(-3, 3);
			else y = (int)between(-100000000, 100000000);
			cout << "1 " << x << ' ' << y << '\n';
			total += x;
		} else {
			int op = 2 + int(rng() & 1);
			i64 k = between(1, total);
			cout << op << ' ' << k << '\n';
		}
	}
}
