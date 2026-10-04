#include <bits/stdc++.h>
using namespace std;
struct D {
	vector<int> p, x;
	D(int n) : p(n + 1), x(n + 1) {
		iota(p.begin(), p.end(), 0);
	}
	pair<int, int> f(int u) {
		if(p[u] == u) return {u, 0};
		auto [r, v] = f(p[u]);
		x[u] ^= v;
		p[u] = r;
		return {r, x[u]};
	}
	bool add(int u, int v) {
		auto [a, xu] = f(u);
		auto [b, xv] = f(v);
		if(a == b) return (xu ^ xv) == 1;
		p[a] = b;
		x[a] = xu ^ xv ^ 1;
		return true;
	}
};
int main() {
	int n, m;
	cin >> n >> m;
	vector<array<int, 3>> e(m);
	for(auto &z : e) cin >> z[0] >> z[1] >> z[2];
	sort(e.begin(), e.end(), [](auto &a, auto &b) { return a[2] < b[2]; });
	D d(n);
	for(auto z : e)
		if(!d.add(z[0], z[1])) {
			cout << z[2] << '\n';
			return 0;
		}
	cout << -1 << '\n';
}
