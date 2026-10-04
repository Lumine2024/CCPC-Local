#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m;
	cin >> n >> m;
	vector<vector<int>> w(n + 1);
	for(int i = 0, u, v, x; i < m; i++) {
		cin >> u >> v >> x;
		w[u].push_back(x);
		w[v].push_back(x);
	}
	long long ans = LLONG_MAX;
	for(auto &a : w)
		if(a.size() > 1) {
			nth_element(a.begin(), a.begin() + 1, a.end());
			ans = min(ans, 1LL * a[0] + a[1]);
		}
	cout << (ans == LLONG_MAX ? -1 : ans) << '\n';
}
