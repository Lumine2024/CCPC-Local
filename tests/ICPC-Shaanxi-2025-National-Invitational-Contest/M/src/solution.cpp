#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<vector<int>> g(n + 1);
	for(int i = 1, u, v; i < n; i++) {
		cin >> u >> v;
		g[u].push_back(v);
		g[v].push_back(u);
	}
	const int INF = 1e9;
	vector<int> dist(n + 1, INF), owner(n + 1, INF);
	using State = tuple<int, int, int>;
	priority_queue<State, vector<State>, greater<State>> pq;
	for(int v = 1; v <= n; v++)
		if(g[v].size() > 2) {
			dist[v] = 0;
			owner[v] = v;
			pq.emplace(0, v, v);
		}
	while(!pq.empty()) {
		auto [d, c, v] = pq.top();
		pq.pop();
		if(d != dist[v] || c != owner[v]) continue;
		for(int w : g[v])
			if(make_pair(d + 1, c) < make_pair(dist[w], owner[w])) {
				dist[w] = d + 1;
				owner[w] = c;
				pq.emplace(d + 1, c, w);
			}
	}
	constexpr int LOG = 19;
	vector<array<int, LOG>> up(n + 1);
	vector<int> depth(n + 1), pref(n + 1), par(n + 1);
	vector<int> order;
	order.reserve(n);
	order.push_back(1);
	for(size_t i = 0; i < order.size(); i++) {
		int v = order[i];
		for(int w : g[v])
			if(w != par[v]) {
				par[w] = v;
				depth[w] = depth[v] + 1;
				pref[w] = pref[v] + (owner[w] != owner[v]);
				up[w][0] = v;
				for(int j = 1; j < LOG; j++) up[w][j] = up[up[w][j - 1]][j - 1];
				order.push_back(w);
			}
	}
	auto lca = [&](int u, int v) {
		if(depth[u] < depth[v]) swap(u, v);
		int delta = depth[u] - depth[v];
		for(int j = 0; j < LOG; j++)
			if(delta >> j & 1) u = up[u][j];
		if(u == v) return u;
		for(int j = LOG - 1; j >= 0; j--)
			if(up[u][j] != up[v][j]) u = up[u][j], v = up[v][j];
		return up[u][0];
	};
	int q;
	cin >> q;
	while(q--) {
		int u, v;
		cin >> u >> v;
		int w = lca(u, v);
		cout << pref[u] + pref[v] - 2 * pref[w] + 1 << '\n';
	}
}
