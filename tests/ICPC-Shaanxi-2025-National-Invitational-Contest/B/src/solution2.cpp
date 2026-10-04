#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<int> a(n), spf(1000001);
	for(int &x : a) cin >> x;
	for(int p = 2; p <= 1000000; p++)
		if(!spf[p])
			for(int j = p; j <= 1000000; j += p)
				if(!spf[j]) spf[j] = p;
	vector<vector<pair<int, int>>> fac(n);
	for(int i = 0; i < n; i++) {
		int v = a[i];
		while(v > 1) {
			int p = spf[v], e = 0;
			while(v % p == 0) v /= p, ++e;
			fac[i].emplace_back(p, e);
		}
	}
	vector<map<int, deque<int>>> groups(1000001);
	vector<int> w(n);
	int needed = 0;
	auto sole = [&](const map<int, deque<int>> &mp) {
		if(mp.empty()) return -1;
		auto &q = mp.rbegin()->second;
		return q.size() == 1 ? q.front() : -1;
	};
	auto change = [&](int i, int d) {
		if(i < 0) return;
		if(!w[i]) ++needed;
		w[i] += d;
		if(!w[i]) --needed;
	};
	auto insert = [&](int i) {
		for(auto [p, e] : fac[i]) {
			auto &mp = groups[p];
			change(sole(mp), -1);
			mp[e].push_back(i);
			change(sole(mp), 1);
		}
	};
	auto erase = [&](int i) {
		for(auto [p, e] : fac[i]) {
			auto &mp = groups[p];
			change(sole(mp), -1);
			auto &q = mp[e];
			q.pop_front();
			if(q.empty()) mp.erase(e);
			change(sole(mp), 1);
		}
	};
	long long ans = 0;
	int r = 0;
	for(int l = 0; l < n; l++) {
		while(r < n && (r - l < 2 || needed == r - l)) insert(r++);
		if(r - l >= 2 && needed < r - l) ans += n - r + 1;
		erase(l);
	}
	cout << ans << '\n';
}
