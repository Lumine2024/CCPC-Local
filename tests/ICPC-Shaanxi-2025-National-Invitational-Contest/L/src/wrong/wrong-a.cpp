#include <bits/stdc++.h>
using namespace std;
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &i : a) cin >> i;
	int m;
	cin >> m;
	long long lo = 0, hi = 1e18;
	while(m--) {
		int t;
		long long x;
		cin >> t >> x;
		if(t == 1) lo = max(lo, x);
		else hi = min(hi, x);
	}
	int ans = 4;
	for(int s = 1; s < (1 << n); s++) {
		int sum = 0;
		for(int i = 0; i < n; i++)
			if(s >> i & 1) sum += a[i];
		if(lo <= sum && sum <= hi)
			ans = min(ans, __builtin_popcount((unsigned)s));
	}
	cout << (ans == 4 ? -1 : ans) << '\n';
}
