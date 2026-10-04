#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	string a;
	cin >> n >> m >> a;
	int d = gcd(n, m);
	vector<array<int, 2>> cnt(d);
	for(int i = 0; i < n; i++) cnt[i % d][a[i] - '0']++;
	long long ans = 0;
	for(auto c : cnt) ans += max(c[0], c[1]);
	cout << ans * m << '\n';
}
