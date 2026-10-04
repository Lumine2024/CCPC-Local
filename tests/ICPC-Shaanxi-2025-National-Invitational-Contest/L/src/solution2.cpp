#include <bits/stdc++.h>
using namespace std;
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(auto &v : a) cin >> v;
	int m;
	cin >> m;
	vector<pair<int, long long>> days(m);
	for(auto &[t, x] : days) cin >> t >> x;
	int best = n + 1;
	for(int bag = 1; bag < (1 << n); bag++) {
		bool good = true;
		for(auto [t, x] : days) {
			bool possible = false;
			for(int outfit = bag; outfit; outfit = (outfit - 1) & bag) {
				long long warmth = 0;
				for(int i = 0; i < n; i++)
					if(outfit >> i & 1) warmth += a[i];
				if((t == 1 && warmth >= x) || (t == 2 && warmth <= x)) {
					possible = true;
					break;
				}
			}
			if(!possible) {
				good = false;
				break;
			}
		}
		if(good) best = min(best, __builtin_popcount((unsigned)bag));
	}
	cout << (best == n + 1 ? -1 : best) << '\n';
}
