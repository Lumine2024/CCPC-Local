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
	int q;
	cin >> q;
	while(q--) {
		int s, t;
		cin >> s >> t;
		vector<int> p(n + 1, -1);
		queue<int> b;
		b.push(s);
		p[s] = 0;
		while(!b.empty() && p[t] < 0) {
			int v = b.front();
			b.pop();
			for(int w : g[v])
				if(p[w] < 0) p[w] = v, b.push(w);
		}
		int ans = 0;
		for(int v = t; v; v = p[v]) {
			ans += g[v].size() > 2;
			if(v == s) break;
		}
		cout << ans << '\n';
	}
}
