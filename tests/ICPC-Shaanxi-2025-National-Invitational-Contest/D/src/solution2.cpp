#include <bits/stdc++.h>
using namespace std;

constexpr int MOD = 1000000007;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<int> a(n + 2);
	for(int i = 1; i <= n; ++i) cin >> a[i];
	const int wall = *max_element(a.begin(), a.end()) + m + 1;
	a[0] = a[n + 1] = wall;

	vector<long long> prefix(n + 2);
	for(int i = 1; i <= n; ++i) prefix[i] = prefix[i - 1] + a[i];
	prefix[n + 1] = prefix[n];

	vector<vector<tuple<int, int, int, long long>>> arcs(n + 2);
	vector<int> stack;
	auto consider = [&](int left, int right) {
		if(right - left <= 1) return;
		int maximum = 0;
		for(int i = left + 1; i < right; ++i) maximum = max(maximum, a[i]);
		if(maximum < min(a[left], a[right])) {
			arcs[left].emplace_back(right, right - left - 1, maximum,
									prefix[right - 1] - prefix[left]);
		}
	};
	for(int right = 0; right <= n + 1; ++right) {
		while(!stack.empty() && a[stack.back()] < a[right]) {
			consider(stack.back(), right);
			stack.pop_back();
		}
		if(!stack.empty()) consider(stack.back(), right);
		stack.push_back(right);
	}

	vector<vector<int>> ways(n + 2, vector<int>(m + 1));
	ways[0][0] = 1;
	for(int left = 0; left <= n; ++left) {
		for(int used = 0; used <= m; ++used) {
			int &target = ways[left + 1][used];
			target += ways[left][used];
			if(target >= MOD) target -= MOD;
		}
		for(auto [right, length, maximum, oldSum] : arcs[left]) {
			const int highest = min(a[left], a[right]);
			const long long smallest64 = 1LL * length * (maximum + 1) - oldSum;
			if(smallest64 > m) continue;
			const int smallest = static_cast<int>(smallest64);
			const int choices = min<long long>(highest - maximum,
											   (m - smallest) / length + 1LL);
			for(int residue = 0; residue < length && smallest + residue <= m;
				++residue) {
				long long rolling = 0;
				int j = 0;
				for(int used = residue; smallest + used <= m;
					used += length, ++j) {
					rolling += ways[left][used];
					if(j >= choices)
						rolling -= ways[left][used - choices * length];
					if(rolling < 0) rolling += MOD;
					if(rolling >= MOD) rolling -= MOD;
					int &target = ways[right][smallest + used];
					target += static_cast<int>(rolling);
					if(target >= MOD) target -= MOD;
				}
			}
		}
	}
	cout << ways[n + 1][m] << '\n';
}
