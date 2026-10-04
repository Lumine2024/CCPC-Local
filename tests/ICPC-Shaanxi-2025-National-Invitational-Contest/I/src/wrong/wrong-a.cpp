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
		long long x = 0, y = 0;
		for(int i = 0; i < n % 4; i++) {
			char c = p[i];
			x += (c == 'E') - (c == 'W');
			y += (c == 'N') - (c == 'S');
		}
		cout << x + y << '\n';
	}
}
