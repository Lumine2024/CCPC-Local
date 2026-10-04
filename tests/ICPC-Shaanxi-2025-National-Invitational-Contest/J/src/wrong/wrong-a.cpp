#include <bits/stdc++.h>
using namespace std;
int main() {
	int t;
	cin >> t;
	while(t--) {
		int n, k = 0;
		cin >> n;
		for(int i = 0, x; i < n; i++) {
			cin >> x;
			k += x == 3;
		}
		cout << (gcd(n, k) == 1 ? "Yes" : "No") << '\n';
	}
}
