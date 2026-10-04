#include <bits/stdc++.h>
using namespace std;
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &i : a) cin >> i;
	int m;
	cin >> m;
	long long need = 0;
	while(m--) {
		int t;
		long long x;
		cin >> t >> x;
		if(t == 1) need = max(need, x);
	}
	sort(a.rbegin(), a.rend());
	long long s = 0;
	for(int i = 0; i < n; i++) {
		s += a[i];
		if(s >= need) {
			cout << i + 1 << '\n';
			return 0;
		}
	}
	cout << -1 << '\n';
}
