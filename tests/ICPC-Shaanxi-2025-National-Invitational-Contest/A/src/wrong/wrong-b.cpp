#include <bits/stdc++.h>
using namespace std;
// Incorrect: reaching preference zero is treated as a secured vote, saving one
// yuan per convert.
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
			if(y > 0) pos += x;
			if(y < 0) neg += x;
		} else {
			long long k;
			cin >> k;
			long long need = max(0LL, k - (op == 2 ? pos : neg)), cost = 0;
			while(need) {
				auto it =
					op == 2 ? prev(count.upper_bound(0)) : count.lower_bound(0);
				int y = it->first;
				long long take = min(need, it->second);
				cost += take * abs((long long)y);
				if(op == 2 && y < 0) neg -= take;
				if(op == 3 && y > 0) pos -= take;
				it->second -= take;
				if(!it->second) count.erase(it);
				count[op == 2 ? 1 : -1] += take;
				if(op == 2) pos += take;
				else neg += take;
				need -= take;
			}
			cout << cost << '\n';
		}
	}
}
