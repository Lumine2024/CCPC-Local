#include <bits/stdc++.h>
using namespace std;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int q;
	cin >> q;
	map<int, long long> count;
	long long positive = 0, negative = 0;
	while(q--) {
		int op;
		cin >> op;
		if(op == 1) {
			long long x;
			int y;
			cin >> x >> y;
			count[y] += x;
			if(y > 0) positive += x;
			if(y < 0) negative += x;
			continue;
		}
		long long k;
		cin >> k;
		long long need = max(0LL, k - (op == 2 ? positive : negative));
		long long cost = 0;
		while(need > 0) {
			if(op == 2) {
				auto it = prev(count.upper_bound(0));
				int y = it->first;
				long long take = min(need, it->second);
				cost += take * (1LL - y);
				if(y < 0) negative -= take;
				if(take == it->second) count.erase(it);
				else it->second -= take;
				count[1] += take;
				positive += take;
				need -= take;
			} else {
				auto it = count.lower_bound(0);
				int y = it->first;
				long long take = min(need, it->second);
				cost += take * (1LL + y);
				if(y > 0) positive -= take;
				if(take == it->second) count.erase(it);
				else it->second -= take;
				count[-1] += take;
				negative += take;
				need -= take;
			}
		}
		cout << cost << '\n';
	}
}
