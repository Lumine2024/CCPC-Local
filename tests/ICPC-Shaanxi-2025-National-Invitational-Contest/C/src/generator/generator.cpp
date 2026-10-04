#include <bits/stdc++.h>
using namespace std;
int main(int argc, char **argv) {
	if(argc != 3) return 1;
	string t = argv[1];
	uint64_t seed = stoull(argv[2]);
	mt19937_64 rng(seed);
	if(t == "sample") {
		cout << "4 3\n1 2\n2 3\n3 4\n2\n2 4\n1 4\n";
		return 0;
	}
	if(t == "empty") {
		cout << "2 0\n0\n";
		return 0;
	}
	int n = t == "random-small" ? 3 + int(rng() % 25) : 500000;
	vector<pair<int, int>> e;
	if(t == "path-large") {
		for(int i = 1; i < n; i++) e.push_back({i, i + 1});
	} else if(t == "star-large") {
		for(int i = 2; i <= n; i++) e.push_back({1, i});
	} else if(t == "nested-large") {
		for(int i = 1; i < n; i++) e.push_back({i, i + 1});
		for(int i = 2; i < n / 2; i++) e.push_back({i, n - i + 1});
	} else {
		for(int i = 1; i < n; i++) e.push_back({i, i + 1});
		for(int i = 3; i <= n; i++)
			if(t == "fan-large" || t == "random-small" || rng() % 2 == 0)
				e.push_back({1, i});
	}
	shuffle(e.begin(), e.end(), rng);
	int m;
	if(t == "initial-all") m = e.size();
	else if(t == "query-all") m = 0;
	else if(t == "random-small") m = int(rng() % (e.size() + 1));
	else m = e.size() / 2;
	cout << n << ' ' << m << '\n';
	for(int i = 0; i < m; i++) cout << e[i].first << ' ' << e[i].second << '\n';
	cout << e.size() - m << '\n';
	for(int i = m; i < (int)e.size(); i++)
		cout << e[i].first << ' ' << e[i].second << '\n';
}
