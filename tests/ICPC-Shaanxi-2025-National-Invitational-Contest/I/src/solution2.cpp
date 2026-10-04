#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int t;
	cin >> t;
	while(t--) {
		long long n;
		string s;
		cin >> n >> s;
		vector<pair<long long, long long>> v(13);
		set<pair<long long, long long>> seen{{0, 0}};
		long long x = 0, y = 0;
		for(int i = 1; i <= 12; i++) {
			int dx = 0, dy = 0;
			if(s[(i - 1) % 4] == 'N') dy = 1;
			if(s[(i - 1) % 4] == 'S') dy = -1;
			if(s[(i - 1) % 4] == 'E') dx = 1;
			if(s[(i - 1) % 4] == 'W') dx = -1;
			do {
				x += dx;
				y += dy;
			} while(seen.count({x, y}));
			seen.insert({x, y});
			v[i] = {x, y};
		}
		if(n <= 12) {
			cout << v[n].first + v[n].second << '\n';
			continue;
		}
		int rem = n % 4;
		long long cycles = n / 4;
		long long base = v[4 + rem].first + v[4 + rem].second;
		long long delta = v[8 + rem].first + v[8 + rem].second - base;
		cout << base + (cycles - 1) * delta << '\n';
	}
}
