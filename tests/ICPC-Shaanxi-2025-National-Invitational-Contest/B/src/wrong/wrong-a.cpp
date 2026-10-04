#include <bits/stdc++.h>
using namespace std;
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(auto &x : a) cin >> x;
	long long ans = 0;
	for(int l = 0; l < n; l++) {
		unordered_set<int> s;
		bool ok = false;
		for(int r = l; r < n; r++) {
			if(!s.insert(a[r]).second) ok = true;
			if(ok) ans++;
		}
	}
	cout << ans << '\n';
}
