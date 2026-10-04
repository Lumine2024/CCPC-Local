#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m, k;
	cin >> n >> m >> k;
	int nodes = 1 << n;
	vector<vector<int>> parents(nodes), children(nodes);
	vector<int> remaining(nodes);
	for(int i = 0, u, v; i < m; i++) {
		cin >> u >> v;
		children[u].push_back(v);
		parents[v].push_back(u);
		remaining[u]++;
	}
	queue<int> work;
	for(int i = 0; i < nodes; i++)
		if(!remaining[i]) work.push(i);
	vector<int> sg(nodes);
	while(!work.empty()) {
		int u = work.front();
		work.pop();
		vector<char> exists(children[u].size() + 1);
		for(int v : children[u])
			if(sg[v] < (int)exists.size()) exists[sg[v]] = 1;
		while(exists[sg[u]]) sg[u]++;
		for(int p : parents[u])
			if(--remaining[p] == 0) work.push(p);
	}
	bitset<512> win;
	win.set();
	win.reset(0);
	vector<bitset<512>> tree(nodes);
	array<bitset<512>, 512> shifted;
	for(int piece = k - 1; piece >= 0; piece--) {
		array<bool, 512> prepared{};
		for(int v = 0; v < nodes; v++) {
			int g = sg[v];
			if(!prepared[g]) {
				prepared[g] = true;
				shifted[g].reset();
				for(int x = 0; x < 512; x++)
					if(win.test(x ^ g)) shifted[g].set(x);
			}
			tree[v] = shifted[g];
		}
		for(int b = n - 1; b >= 0; b--) {
			bool first = (piece * n + b) % 2 == 0;
			for(int v = 0; v < (1 << b); v++) {
				if(first) tree[v] |= tree[v + (1 << b)];
				else tree[v] &= tree[v + (1 << b)];
			}
		}
		win = tree[0];
	}
	cout << (win.test(0) ? "First" : "Second") << '\n';
}
