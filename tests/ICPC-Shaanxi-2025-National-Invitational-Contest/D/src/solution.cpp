#include <bits/stdc++.h>
using namespace std;

static constexpr int MOD = 1000000007;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);

	int n, m;
	cin >> n >> m;
	vector<int> a(n + 2);
	int tallest = 0;
	for(int i = 1; i <= n; ++i) {
		cin >> a[i];
		tallest = max(tallest, a[i]);
	}
	a[0] = a[n + 1] = tallest + m + 1;

	vector<vector<int>> dp(n + 2, vector<int>(m + 1));
	vector<int> window(m + 1);
	dp[0][0] = 1;

	for(int u = 0; u <= n; ++u) {
		for(int used = 0; used <= m; ++used) {
			int &dest = dp[u + 1][used];
			dest += dp[u][used];
			if(dest >= MOD) dest -= MOD;
		}

		int interiorMax = -1;
		long long interiorSum = 0;
		for(int v = u + 2; v <= n + 1; ++v) {
			const int last = v - 1;
			interiorMax = max(interiorMax, a[last]);
			interiorSum += a[last];
			if(interiorMax >= a[u]) break;
			if(interiorMax >= a[v]) continue;

			const int length = v - u - 1;
			const int minHeight = interiorMax + 1;
			const int maxHeight = min(a[u], a[v]);
			const long long firstCost64 =
				1LL * length * minHeight - interiorSum;
			if(firstCost64 > m) continue;
			const int firstCost = static_cast<int>(firstCost64);
			const int count = min<long long>(maxHeight - minHeight + 1LL,
											 (m - firstCost) / length + 1LL);
			const int cutoff = count * length;

			for(int t = 0; t + firstCost <= m; ++t) {
				long long value = dp[u][t];
				if(t >= length) value += window[t - length];
				if(t >= cutoff) value -= dp[u][t - cutoff];
				if(value < 0) value += MOD;
				if(value >= MOD) value -= MOD;
				window[t] = static_cast<int>(value);

				int &dest = dp[v][t + firstCost];
				dest += window[t];
				if(dest >= MOD) dest -= MOD;
			}
		}
	}
	cout << dp[n + 1][m] << '\n';
}
