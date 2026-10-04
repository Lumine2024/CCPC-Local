#include <bits/stdc++.h>
using namespace std;
// Incorrect: undecided voters are counted as confirmed votes for either side.
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int q;
	cin >> q;
	map<int, long long> count;
	long long pos = 0, neg = 0;
	while(q--) {
		int op;
		cin >> op;
		if(op == 1) {
			long long x;
			int y;
			cin >> x >> y;
			count[y] += x;
			if(y >= 0) pos += x;
			if(y <= 0) neg += x;
		} else {
			long long k;
			cin >> k;
			long long need = max(0LL, k - (op == 2 ? pos : neg)), cost = 0;
			while(need) {
				auto it =
					op == 2 ? prev(count.lower_bound(0)) : count.upper_bound(0);
				int y = it->first;
				long long take = min(need, it->second);
				cost += take * (op == 2 ? 1LL - y : 1LL + y);
				it->second -= take;
				if(!it->second) count.erase(it);
				count[op == 2 ? 1 : -1] += take;
				if(op == 2) {
					pos += take;
					neg -= take;
				} else {
					neg += take;
					pos -= take;
				}
				need -= take;
			}
			cout << cost << '\n';
		}
	}
}
