#include <bits/stdc++.h>
using namespace std;

// Independent direct dynamic programming reference. It is deliberately used
// only on small generated cases because its cost is linear in each interval.
static constexpr uint64_t CAP = 1000000001ULL;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, q;
	string s;
	cin >> n >> q >> s;
	while(q--) {
		int l, r;
		uint64_t k;
		cin >> l >> r >> k;
		--l;
		--r;
		if(l == r) {
			cout << -1 << '\n';
			continue;
		}
		vector<array<int, 5>> next(r + 2);
		next[r].fill(r);
		vector<uint64_t> ways(r + 2);
		ways[r] = 1;
		for(int p = r - 1; p >= l + 1; --p) {
			next[p] = next[p + 1];
			next[p][s[p] - 'a'] = p;
			uint64_t total = 1;
			for(int c = 0; c < 5; ++c)
				if(next[p][c] < r)
					total = min(CAP, total + ways[next[p][c] + 1]);
			ways[p] = total;
		}
		int tail = s[r] - 'a', p = l + 1;
		uint32_t hash = s[l] - 'a' + 1;
		while(true) {
			bool selected = false, finished = false;
			for(int c = 0; c < 5; ++c) {
				uint64_t count = c == tail;
				if(p < r && next[p][c] < r)
					count = min(CAP, count + ways[next[p][c] + 1]);
				if(k > count) {
					k -= count;
					continue;
				}
				selected = true;
				if(c == tail) {
					if(k == 1) {
						cout << (hash * 1331U + uint32_t(c + 1)) << '\n';
						finished = true;
						break;
					}
					--k;
				}
				hash = hash * 1331U + uint32_t(c + 1);
				p = next[p][c] + 1;
				break;
			}
			if(!selected) {
				cout << -1 << '\n';
				break;
			}
			if(finished) break;
		}
	}
}
