#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<int> a(n), spf(1000001);
	for(int &x : a) cin >> x;
	for(int i = 2; i <= 1000000; i++)
		if(!spf[i]) {
			spf[i] = i;
			if(1LL * i * i <= 1000000)
				for(int j = i * i; j <= 1000000; j += i)
					if(!spf[j]) spf[j] = i;
		}
	vector<vector<pair<int, int>>> f(n);
	for(int i = 0; i < n; i++) {
		int x = a[i];
		while(x > 1) {
			int p = spf[x], e = 0;
			do {
				x /= p;
				++e;
			} while(x > 1 && spf[x] == p);
			f[i].push_back({p, e});
		}
	}
	vector<set<pair<int, int>>> s(1000001);
	vector<int> cert(n);
	int essential = 0;
	auto owner = [&](const set<pair<int, int>> &t) {
		if(t.empty()) return -1;
		auto it = prev(t.end());
		if(it != t.begin() && prev(it)->first == it->first) return -1;
		return it->second;
	};
	auto change = [&](int i, int d) {
		if(i < 0) return;
		if(cert[i] == 0) ++essential;
		cert[i] += d;
		if(cert[i] == 0) --essential;
	};
	auto upd = [&](int i, bool add) {
		for(auto [p, e] : f[i]) {
			auto &t = s[p];
			change(owner(t), -1);
			if(add) t.insert({e, i});
			else t.erase({e, i});
			change(owner(t), 1);
		}
	};
	long long ans = 0;
	int r = 0;
	for(int l = 0; l < n; l++) {
		while(r < n && (r - l < 2 || essential == r - l)) upd(r++, true);
		if(r - l >= 2 && essential < r - l) ans += n - r + 1;
		upd(l, false);
	}
	cout << ans << '\n';
}
