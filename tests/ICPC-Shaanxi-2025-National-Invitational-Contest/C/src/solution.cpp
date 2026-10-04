#include <bits/stdc++.h>
using namespace std;
using ll = long long;
struct Edge {
	int u, v;
};
static unsigned long long key(int u, int v) {
	if(u > v) swap(u, v);
	return (unsigned long long)(unsigned int)u << 32 | (unsigned int)v;
}
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<Edge> edges;
	edges.reserve(1000000);
	for(int i = 0, u, v; i < m; i++) {
		cin >> u >> v;
		edges.push_back({u, v});
	}
	int q;
	cin >> q;
	for(int i = 0, u, v; i < q; i++) {
		cin >> u >> v;
		edges.push_back({u, v});
	}
	int E = edges.size();
	vector<vector<pair<int, int>>> adj(n + 1);
	vector<int> rem(n + 1);
	unordered_map<unsigned long long, int> id;
	id.reserve(E * 2 + 1);
	id.max_load_factor(0.7);
	for(int i = 0; i < E; i++) {
		auto [u, v] = edges[i];
		adj[u].push_back({v, i});
		adj[v].push_back({u, i});
		rem[u]++;
		rem[v]++;
		id[key(u, v)] = i;
	}
	queue<int> que;
	for(int v = 1; v <= n; v++)
		if(rem[v] <= 2) que.push(v);
	vector<char> gone(n + 1);
	vector<vector<pair<int, int>>> out(n + 1);
	for(; !que.empty();) {
		int v = que.front();
		que.pop();
		if(gone[v] || rem[v] > 2) continue;
		gone[v] = 1;
		for(auto [w, e] : adj[v])
			if(!gone[w]) {
				out[v].push_back({w, e});
				if(--rem[w] == 2) que.push(w);
			}
	}
	vector<vector<pair<int, int>>> tri(E);
	for(int v = 1; v <= n; v++)
		if(out[v].size() == 2) {
			int a = out[v][0].first, b = out[v][1].first, e1 = out[v][0].second,
				e2 = out[v][1].second;
			auto it = id.find(key(a, b));
			if(it == id.end()) continue;
			int e3 = it->second;
			tri[e1].push_back({e2, e3});
			tri[e2].push_back({e1, e3});
			tri[e3].push_back({e1, e2});
		}
	vector<char> active(E);
	vector<int> deg(n + 1);
	vector<ll> incoming(n + 1);
	ll products = 0, triangles = 0;
	auto sum = [&](int v) {
		ll s = incoming[v];
		for(auto [w, e] : out[v])
			if(active[e]) s += deg[w] - 1;
		return s;
	};
	auto insert = [&](int i) {
		auto [u, v] = edges[i];
		products += sum(u) + sum(v) + 1LL * deg[u] * deg[v];
		for(auto [a, b] : tri[i])
			if(active[a] && active[b]) triangles++;
		// The edge enters its tail's outgoing list with the old degree
		// contribution.
		int tail = -1, head = -1;
		for(auto [w, e] : out[u])
			if(e == i) {
				tail = u;
				head = v;
				break;
			}
		if(tail < 0) {
			tail = v;
			head = u;
		}
		incoming[head] += deg[tail] - 1;
		active[i] = 1;
		deg[u]++;
		deg[v]++;
		for(auto [w, e] : out[u])
			if(active[e]) incoming[w]++;
		for(auto [w, e] : out[v])
			if(active[e]) incoming[w]++;
	};
	for(int i = 0; i < m; i++) insert(i);
	cout << 2 * (products - 3 * triangles) << '\n';
	for(int i = m; i < E; i++) {
		insert(i);
		cout << 2 * (products - 3 * triangles) << '\n';
	}
}
