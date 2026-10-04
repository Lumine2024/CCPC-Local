#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m, k;
	cin >> n >> m >> k;
	int N = 1 << n;
	vector<vector<int>> adj(N);
	vector<int> deg(N);
	for(int i = 0, u, v; i < m; i++) {
		cin >> u >> v;
		adj[u].push_back(v);
		deg[v]++;
	}
	queue<int> q;
	for(int i = 0; i < N; i++)
		if(!deg[i]) q.push(i);
	vector<int> ord;
	while(!q.empty()) {
		int u = q.front();
		q.pop();
		ord.push_back(u);
		for(int v : adj[u])
			if(--deg[v] == 0) q.push(v);
	}
	vector<int> g(N);
	for(int j = N - 1; j >= 0; j--) {
		int u = ord[j];
		vector<char> s(adj[u].size() + 1);
		for(int v : adj[u])
			if(g[v] < (int)s.size()) s[g[v]] = 1;
		while(s[g[u]]) g[u]++;
	}
	bitset<512> win;
	win.set();
	win.reset(0);
	vector<bitset<512>> dp(N);
	for(int row = k - 1; row >= 0; row--) {
		for(int v = 0; v < N; v++) {
			dp[v].reset();
			for(int x = 0; x < 512; x++)
				if(win.test(x ^ g[v])) dp[v].set(x);
		}
		for(int bit = 0; bit < n; bit++)
			for(int v = 0; v < N; v++)
				if(!(v & (1 << bit))) {
					if((row * n + n - 1 - bit) % 2 == 0)
						dp[v] |= dp[v | (1 << bit)];
					else dp[v] &= dp[v | (1 << bit)];
				}
		win = dp[0];
	}
	cout << (win.test(0) ? "First" : "Second") << '\n';
}
