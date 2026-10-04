#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int t;
	cin >> t;
	while(t--) {
		long long n;
		string p;
		cin >> n >> p;
		set<pair<long long, long long>> seen{{0, 0}};
		long long x = 0, y = 0;
		vector<long long> s(9);
		for(int i = 1; i <= 8; i++) {
			char c = p[(i - 1) % 4];
			int dx = (c == 'E') - (c == 'W'), dy = (c == 'N') - (c == 'S');
			do {
				x += dx;
				y += dy;
			} while(seen.count({x, y}));
			seen.insert({x, y});
			s[i] = x + y;
		}
		if(n <= 8) cout << s[n] << '\n';
		else cout << (n / 4) * s[4] + s[n % 4] << '\n';
	}
}
