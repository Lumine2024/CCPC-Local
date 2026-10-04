#include <bits/stdc++.h>
using namespace std;
using i64 = long long;
struct E {
	int x, y;
};
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, m;
	cin >> n >> m;
	vector<E> e;
	e.reserve(1000000);
	for(int j = 0, x, y; j < m; j++) {
		cin >> x >> y;
		e.push_back({x, y});
	}
	int q;
	cin >> q;
	for(int j = 0, x, y; j < q; j++) {
		cin >> x >> y;
		e.push_back({x, y});
	}
	int sz = e.size();
	vector<vector<pair<int, int>>> graph(n + 1), forward(n + 1);
	vector<int> degree(n + 1);
	for(int j = 0; j < sz; j++) {
		auto [x, y] = e[j];
		graph[x].push_back({y, j});
		graph[y].push_back({x, j});
		degree[x]++;
		degree[y]++;
	}
	for(int x = 1; x <= n; x++) sort(graph[x].begin(), graph[x].end());
	deque<int> ready;
	for(int x = 1; x <= n; x++)
		if(degree[x] <= 2) ready.push_back(x);
	vector<unsigned char> removed(n + 1);
	while(!ready.empty()) {
		int x = ready.front();
		ready.pop_front();
		if(removed[x] || degree[x] > 2) continue;
		removed[x] = 1;
		for(auto [y, j] : graph[x])
			if(!removed[y]) {
				forward[x].push_back({y, j});
				if(--degree[y] == 2) ready.push_back(y);
			}
	}
	vector<array<int, 3>> triangles;
	triangles.reserve(sz);
	vector<vector<int>> memberships(sz);
	for(int x = 1; x <= n; x++)
		if(forward[x].size() == 2) {
			auto [a, ea] = forward[x][0];
			auto [b, eb] = forward[x][1];
			auto it =
				lower_bound(graph[a].begin(), graph[a].end(), make_pair(b, -1));
			if(it == graph[a].end() || it->first != b) continue;
			int ec = it->second, t = triangles.size();
			triangles.push_back({ea, eb, ec});
			memberships[ea].push_back(t);
			memberships[eb].push_back(t);
			memberships[ec].push_back(t);
		}
	vector<unsigned char> live(sz);
	vector<int> d(n + 1), tail(sz), head(sz);
	vector<i64> fromEarlier(n + 1);
	for(int x = 1; x <= n; x++)
		for(auto [y, j] : forward[x]) tail[j] = x, head[j] = y;
	auto neighborSum = [&](int x) {
		i64 z = fromEarlier[x];
		for(auto [y, j] : forward[x])
			if(live[j]) z += d[y] - 1;
		return z;
	};
	i64 middle = 0, tcount = 0;
	if(m == 0) cout << 0 << '\n';
	for(int j = 0; j < sz; j++) {
		auto [x, y] = e[j];
		middle += neighborSum(x) + neighborSum(y) + 1LL * d[x] * d[y];
		for(int t : memberships[j]) {
			int count = 0;
			for(int z : triangles[t]) count += live[z];
			if(count == 2) tcount++;
		}
		fromEarlier[head[j]] += d[tail[j]] - 1;
		live[j] = 1;
		++d[x];
		++d[y];
		for(auto [z, k] : forward[x])
			if(live[k]) ++fromEarlier[z];
		for(auto [z, k] : forward[y])
			if(live[k]) ++fromEarlier[z];
		if(j == m - 1) cout << 2 * (middle - 3 * tcount) << '\n';
		if(j >= m) cout << 2 * (middle - 3 * tcount) << '\n';
	}
}
