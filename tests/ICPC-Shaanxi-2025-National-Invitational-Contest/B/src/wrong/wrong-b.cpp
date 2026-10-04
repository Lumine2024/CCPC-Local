#include <bits/stdc++.h>
using namespace std;
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(auto &x : a) cin >> x;
	long long ans = 0;
	for(int l = 0; l < n; l++) {
		bool ok = false;
		for(int r = l; r < n; r++) {
			for(int i = l; i <= r && !ok; i++)
				for(int j = l; j <= r; j++)
					if(i != j && a[j] % a[i] == 0) ok = true;
			if(ok) ans++;
		}
	}
	cout << ans << '\n';
}
