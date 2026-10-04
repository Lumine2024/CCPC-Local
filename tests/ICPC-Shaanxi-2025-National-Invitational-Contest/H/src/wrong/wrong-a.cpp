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
		// Incorrect: assumes the direct two-character subsequence is the only
		// one.
		if(l == r || k != 1) cout << -1 << '\n';
		else
			cout << (uint32_t(s[l - 1] - 'a' + 1) * 1331U +
					 uint32_t(s[r - 1] - 'a' + 1))
				 << '\n';
	}
	return 0;
}
