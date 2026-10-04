#include <bits/stdc++.h>
using namespace std;
struct E {
	int v, w;
};
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<vector<E>> g(n);
	for(int i = 0, u, v, w; i < m; i++) {
		cin >> u >> v >> w;
		--u;
		--v;
		g[u].push_back({v, w});
		g[v].push_back({u, w});
	}
	long long S = LLONG_MAX;
	for(auto &adj : g)
		for(auto a : adj)
			for(auto b : adj)
				if(a.v != b.v) S = min(S, 1LL * a.w + b.w);
	auto feasible = [&](long long d) {
		if(S < d) return false;
		vector<int> color(n, -1);
		queue<int> q;
		for(int s = 0; s < n; s++)
			if(color[s] < 0) {
				color[s] = 0;
				q.push(s);
				while(!q.empty()) {
					int u = q.front();
					q.pop();
					for(auto z : g[u])
						if(z.w < d) {
							if(color[z.v] < 0) {
								color[z.v] = color[u] ^ 1;
								q.push(z.v);
							} else if(color[z.v] == color[u]) return false;
						}
				}
			}
		return true;
	};
	if(S == LLONG_MAX) {
		S = 100000001LL;
	}
	long long lo = 1, hi = S + 1;
	while(lo + 1 < hi) {
		long long mid = (lo + hi) / 2;
		if(feasible(mid)) lo = mid;
		else hi = mid;
	}
	if(S == 100000001LL && feasible(S)) cout << -1 << '\n';
	else cout << lo << '\n';
}
