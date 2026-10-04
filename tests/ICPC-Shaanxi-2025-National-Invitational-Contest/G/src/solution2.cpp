#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m;
	string s;
	cin >> n >> m >> s;
	int g = std::gcd(n, m);
	vector<array<int, 2>> counts(g);
	for(int i = 0; i < n; i++) counts[i % g][s[i] - '0']++;
	long long answer = 0;
	for(int j = 0; j < m; j++) {
		auto [zero, one] = counts[j % g];
		answer += 1LL * g * max(zero, one);
	}
	cout << answer << '\n';
}
