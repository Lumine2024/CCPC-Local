#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<vector<int>> adj(n + 1);
	vector<int> deg(n + 1);
	for(int i = 1, x, y; i < n; i++) {
		cin >> x >> y;
		adj[x].push_back(y);
		adj[y].push_back(x);
		deg[x]++;
		deg[y]++;
	}
	deque<int> bfs;
	vector<int> country(n + 1);
	for(int x = 1; x <= n; x++)
		if(deg[x] >= 3) country[x] = x, bfs.push_back(x);
	while(!bfs.empty()) {
		int x = bfs.front();
		bfs.pop_front();
		for(int y : adj[x])
			if(!country[y]) country[y] = country[x], bfs.push_back(y);
	}
	vector<int> parent(n + 1), dep(n + 1), size(n + 1, 1), heavy(n + 1),
		top(n + 1), border(n + 1), order;
	size[0] = 0;
	order.reserve(n);
	order.push_back(1);
	for(size_t i = 0; i < order.size(); i++) {
		int x = order[i];
		for(int y : adj[x])
			if(y != parent[x]) {
				parent[y] = x;
				dep[y] = dep[x] + 1;
				border[y] = border[x] + (country[y] != country[x]);
				order.push_back(y);
			}
	}
	for(int i = n - 1; i >= 1; i--) {
		int x = order[i], p = parent[x];
		size[p] += size[x];
		if(size[x] > size[heavy[p]]) heavy[p] = x;
	}
	for(int x : order)
		if(x == 1 || heavy[parent[x]] != x)
			for(int y = x; y; y = heavy[y]) top[y] = x;
	auto ancestor = [&](int x, int y) {
		while(top[x] != top[y]) {
			if(dep[top[x]] < dep[top[y]]) swap(x, y);
			x = parent[top[x]];
		}
		return dep[x] < dep[y] ? x : y;
	};
	int q;
	cin >> q;
	while(q--) {
		int u, v;
		cin >> u >> v;
		int w = ancestor(u, v);
		cout << border[u] + border[v] - 2 * border[w] + 1 << '\n';
	}
}
