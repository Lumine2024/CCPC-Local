#include <bits/stdc++.h>
using namespace std;
long long c3(long long x) {
	return x * (x - 1) * (x - 2) / 6;
}
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &x : a) cin >> x;
	auto f = [&](int A, int B) {
		int t = min(A, B);
		long long S = c3(B + 1) - c3(B - t + 1), base = 1LL * B * (B - 1) / 2;
		return (S + (B - 1) * base) / (A + B - 1);
	};
	for(int i = 0; i < n; i++)
		cout << (f(a[i], a[(i + n - 1) % n]) + f(a[i], a[(i + 1) % n])) %
					998244353
			 << (i + 1 == n ? '\n' : ' ');
}
