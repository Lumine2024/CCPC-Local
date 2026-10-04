#include <bits/stdc++.h>
using namespace std;
struct DSU {
	vector<int> p, sz;
	DSU(int n) : p(n), sz(n, 1) {
		iota(p.begin(), p.end(), 0);
	}
	int find(int x) {
		while(p[x] != x) {
			p[x] = p[p[x]];
			x = p[x];
		}
		return x;
	}
	void merge(int a, int b) {
		a = find(a);
		b = find(b);
		if(a != b) {
			if(sz[a] < sz[b]) swap(a, b);
			p[b] = a;
			sz[a] += sz[b];
		}
	}
};
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int t;
	cin >> t;
	while(t--) {
		int n, k = 0;
		cin >> n;
		for(int i = 0, x; i < n; i++) {
			cin >> x;
			k += x == 3;
		}
		DSU d(n);
		for(int i = 0; i < n; i++) d.merge(i, (i + (i < k ? 3 : 2)) % n);
		bool ok = true;
		for(int i = 1; i < n; i++)
			if(d.find(i) != d.find(0)) {
				ok = false;
				break;
			}
		cout << (ok ? "Yes" : "No") << '\n';
	}
}
