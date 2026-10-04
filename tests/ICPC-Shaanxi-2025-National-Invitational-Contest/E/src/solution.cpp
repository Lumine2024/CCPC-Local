#include <bits/stdc++.h>
using namespace std;
using Bits = array<uint64_t, 8>;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m, k;
	cin >> n >> m >> k;
	int N = 1 << n;
	vector<vector<int>> out(N);
	vector<int> indeg(N);
	for(int i = 0, u, v; i < m; i++) {
		cin >> u >> v;
		out[u].push_back(v);
		indeg[v]++;
	}
	queue<int> q;
	for(int v = 0; v < N; v++)
		if(!indeg[v]) q.push(v);
	vector<int> order;
	order.reserve(N);
	while(!q.empty()) {
		int u = q.front();
		q.pop();
		order.push_back(u);
		for(int v : out[u])
			if(--indeg[v] == 0) q.push(v);
	}
	vector<int> grundy(N);
	for(int at = N - 1; at >= 0; at--) {
		int u = order[at];
		vector<unsigned char> seen(out[u].size() + 1);
		for(int v : out[u])
			if(grundy[v] < (int)seen.size()) seen[grundy[v]] = 1;
		while(seen[grundy[u]]) grundy[u]++;
	}
	Bits next{};
	for(int x = 1; x < 512; x++) next[x >> 6] |= 1ULL << (x & 63);
	vector<Bits> layer(N);
	array<Bits, 512> perm{};
	array<unsigned char, 512> used{};
	for(int row = k - 1; row >= 0; row--) {
		used.fill(0);
		for(int v = 0; v < N; v++) used[grundy[v]] = 1;
		for(int g = 0; g < 512; g++)
			if(used[g]) {
				perm[g].fill(0);
				for(int x = 0; x < 512; x++)
					if((next[(x ^ g) >> 6] >> ((x ^ g) & 63)) & 1ULL)
						perm[g][x >> 6] |= 1ULL << (x & 63);
			}
		for(int v = 0; v < N; v++) layer[v] = perm[grundy[v]];
		for(int bit = n - 1; bit >= 0; bit--) {
			bool first = ((row * n + bit) & 1) == 0;
			for(int v = 0; v < (1 << bit); v++)
				for(int w = 0; w < 8; w++)
					if(first) layer[v][w] |= layer[v + (1 << bit)][w];
					else layer[v][w] &= layer[v + (1 << bit)][w];
		}
		next = layer[0];
	}
	cout << ((next[0] & 1ULL) ? "First" : "Second") << '\n';
}
