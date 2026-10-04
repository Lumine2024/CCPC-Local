#include <bits/stdc++.h>
using namespace std;
using ll = long long;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<vector<int>> g(n + 1);
	vector<int> d(n + 1);
	auto add = [&](int u, int v) {
		g[u].push_back(v);
		g[v].push_back(u);
		d[u]++;
		d[v]++;
	};
	for(int i = 0, u, v; i < m; i++) {
		cin >> u >> v;
		add(u, v);
	}
	auto answer = [&]() {
		ll z = 0;
		for(int u = 1; u <= n; u++)
			for(int v : g[u])
				if(u < v) z += 2LL * (d[u] - 1) * (d[v] - 1);
		return z;
	};
	cout << answer() << '\n';
	int q;
	cin >> q;
	for(int i = 0, u, v; i < q; i++) {
		cin >> u >> v;
		add(u, v);
		cout << answer() << '\n';
	}
}
