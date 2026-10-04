#include <bits/stdc++.h>
using namespace std;
struct Edge {
	int u, v, w;
};
struct DSU {
	vector<int> p, sz, xr;
	DSU(int n) : p(n + 1), sz(n + 1, 1), xr(n + 1) {
		iota(p.begin(), p.end(), 0);
	}
	pair<int, int> find(int x) {
		if(p[x] == x) return {x, 0};
		auto [r, t] = find(p[x]);
		int v = xr[x] ^ t;
		p[x] = r;
		xr[x] = v;
		return {r, v};
	}
	bool add(int a, int b) {
		auto [ra, xa] = find(a);
		auto [rb, xb] = find(b);
		if(ra == rb) return (xa ^ xb) == 1;
		if(sz[ra] < sz[rb]) {
			swap(ra, rb);
			swap(xa, xb);
		}
		p[rb] = ra;
		xr[rb] = xa ^ xb ^ 1;
		sz[ra] += sz[rb];
		return true;
	}
};
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<Edge> e(m);
	vector<vector<pair<int, int>>> adj(n + 1);
	for(auto &z : e) {
		cin >> z.u >> z.v >> z.w;
		adj[z.u].push_back({z.w, z.v});
		adj[z.v].push_back({z.w, z.u});
	}
	long long S = LLONG_MAX;
	for(int u = 1; u <= n; u++) {
		auto &v = adj[u];
		if(v.size() < 2) continue;
		sort(v.begin(), v.end());
		for(size_t j = 1; j < v.size(); j++)
			if(v[j].second != v[0].second) {
				S = min(S, 1LL * v[0].first + v[j].first);
				break;
			}
	}
	sort(e.begin(), e.end(), [](auto &a, auto &b) { return a.w < b.w; });
	DSU d(n);
	long long B = LLONG_MAX;
	for(auto z : e)
		if(!d.add(z.u, z.v)) {
			B = z.w;
			break;
		}
	long long ans = min(S, B);
	cout << (ans == LLONG_MAX ? -1 : ans) << '\n';
}
