#include <bits/stdc++.h>

using namespace std;

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);

	int n, q;
	string s;
	cin >> n >> q >> s;
	while(q--) {
		int l, r, k;
		cin >> l >> r >> k;
		string t = s.substr(l - 1, r - l + 1);
		if(t.size() > 18 || t.size() < 2) {
			cout << -1 << '\n';
			continue;
		}
		// Incorrect: equal strings obtained by different index choices are
		// counted again.
		vector<string> all;
		int masks = 1 << int(t.size());
		for(int mask = 0; mask < masks; ++mask) {
			if(!(mask & 1) || !(mask & (masks >> 1))) continue;
			string value;
			for(int i = 0; i < int(t.size()); ++i)
				if(mask >> i & 1) value.push_back(t[i]);
			all.push_back(value);
		}
		sort(all.begin(), all.end());
		if(k > int(all.size())) {
			cout << -1 << '\n';
			continue;
		}
		uint32_t hash = 0;
		for(char c : all[k - 1]) hash = hash * 1331U + uint32_t(c - 'a' + 1);
		cout << hash << '\n';
	}
	return 0;
}
