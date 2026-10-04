#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &i : a) cin >> i;
	int m;
	cin >> m;
	long long need = 0, cap = LLONG_MAX;
	for(int i = 0; i < m; i++) {
		int t;
		long long x;
		cin >> t >> x;
		if(t == 1) need = max(need, x);
		else cap = min(cap, x);
	}
	int ans = 4;
	for(int mask = 1; mask < (1 << n); mask++) {
		long long sum = 0;
		int low = INT_MAX;
		for(int i = 0; i < n; i++)
			if(mask >> i & 1) {
				sum += a[i];
				low = min(low, a[i]);
			}
		if(sum >= need && low <= cap)
			ans = min(ans, __builtin_popcount((unsigned)mask));
	}
	cout << (ans == 4 ? -1 : ans) << '\n';
}
