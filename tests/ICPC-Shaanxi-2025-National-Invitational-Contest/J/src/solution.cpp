#include <bits/stdc++.h>
using namespace std;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int T;
	cin >> T;
	while(T--) {
		int n, c3 = 0;
		cin >> n;
		for(int i = 0, x; i < n; i++) {
			cin >> x;
			c3 += x == 3;
		}
		vector<int> a(n, 2);
		for(int i = 0; i < c3; i++) a[i] = 3;
		vector<int> indeg(n);
		for(int i = 0; i < n; i++) indeg[(i + a[i]) % n]++;
		int start = 0, zero = 0;
		for(int i = 0; i < n; i++)
			if(indeg[i] == 0) {
				start = i;
				zero++;
			}
		vector<char> seen(n);
		int pos = start, count = 0;
		while(!seen[pos]) {
			seen[pos] = 1;
			count++;
			pos = (pos + a[pos]) % n;
		}
		cout << ((zero <= 1 && count == n) ? "Yes" : "No") << '\n';
	}
}
