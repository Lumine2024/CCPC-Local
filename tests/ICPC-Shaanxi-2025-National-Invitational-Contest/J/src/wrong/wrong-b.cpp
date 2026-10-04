#include <bits/stdc++.h>
using namespace std;
int main() {
	int t;
	cin >> t;
	while(t--) {
		int n;
		cin >> n;
		vector<int> a(n);
		for(int &i : a) cin >> i;
		bool ok = false;
		for(int s = 0; s < n; s++) {
			vector<char> seen(n);
			int p = s, c = 0;
			while(!seen[p]) {
				seen[p] = 1;
				c++;
				p = (p + a[p]) % n;
			}
			if(c == n) {
				ok = true;
				break;
			}
		}
		cout << (ok ? "Yes" : "No") << '\n';
	}
}
