#include <bits/stdc++.h>
using namespace std;
constexpr int MOD = 1000000007;

// Incorrect: assumes only originally low columns can receive boxes.
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<int> a(n + 2, 1000000000);
	for(int i = 1; i <= n; ++i) cin >> a[i];
	vector<int> dp(m + 1);
	dp[0] = 1;
	for(int i = 1; i <= n; ++i) {
		int capacity = max(0, min(a[i - 1], a[i + 1]) - a[i]);
		capacity = min(capacity, m);
		vector<int> next(m + 1);
		long long window = 0;
		for(int j = 0; j <= m; ++j) {
			window += dp[j];
			if(j > capacity) window -= dp[j - capacity - 1];
			if(window < 0) window += MOD;
			if(window >= MOD) window -= MOD;
			next[j] = static_cast<int>(window);
		}
		dp.swap(next);
	}
	cout << dp[m] << '\n';
}
