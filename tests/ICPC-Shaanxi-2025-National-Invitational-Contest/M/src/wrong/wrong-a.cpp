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
	vector<int> owner(n + 1);
	queue<int> q;
	for(int v = n; v >= 1; v--)
		if(g[v].size() > 2) owner[v] = v, q.push(v);
	while(!q.empty()) {
		int v = q.front();
		q.pop();
		for(int w : g[v])
			if(!owner[w]) owner[w] = owner[v], q.push(w);
	}
	int z;
	cin >> z;
	while(z--) {
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
		set<int> seen;
		for(int v = t; v; v = p[v]) {
			seen.insert(owner[v]);
			if(v == s) break;
		}
		cout << seen.size() << '\n';
	}
}
