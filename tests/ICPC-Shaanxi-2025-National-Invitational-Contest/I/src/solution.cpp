#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int T;
	cin >> T;
	while(T--) {
		long long n;
		string p;
		cin >> n >> p;
		set<pair<long long, long long>> used{{0, 0}};
		pair<long long, long long> cur{0, 0};
		vector<pair<long long, long long>> pos(17);
		for(int i = 1; i <= 16; i++) {
			char c = p[(i - 1) % 4];
			long long dx = (c == 'E') - (c == 'W'),
					  dy = (c == 'N') - (c == 'S');
			do {
				cur.first += dx;
				cur.second += dy;
			} while(used.count(cur));
			used.insert(cur);
			pos[i] = cur;
		}
		pair<long long, long long> a;
		if(n <= 16) a = pos[n];
		else {
			long long q = n / 4, r = n % 4;
			auto b = pos[8 + r], d = pos[12 + r];
			a = {b.first + (q - 2) * (d.first - b.first),
				 b.second + (q - 2) * (d.second - b.second)};
		}
		cout << a.first + a.second << '\n';
	}
}
