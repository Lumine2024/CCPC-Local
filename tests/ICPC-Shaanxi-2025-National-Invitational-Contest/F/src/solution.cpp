#include <bits/stdc++.h>
using namespace std;
constexpr long long MOD = 998244353;
long long choose3(long long x) {
	return x * (x - 1) * (x - 2) / 6;
}
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &x : a) cin >> x;
	vector<long long> inv(200001);
	inv[1] = 1;
	for(int i = 2; i <= 200000; i++)
		inv[i] = MOD - (MOD / i) * inv[MOD % i] % MOD;
	auto contribution = [&](long long A, long long B) {
		long long t = min(A, B);
		long long S = choose3(B + 1) - choose3(B - t + 1);
		long long base = B * (B - 1) / 2;
		return (S + (B - 1) * base) % MOD * inv[A + B - 1] % MOD;
	};
	for(int i = 0; i < n; i++) {
		long long ans = (contribution(a[i], a[(i + n - 1) % n]) +
						 contribution(a[i], a[(i + 1) % n])) %
						MOD;
		if(i) cout << ' ';
		cout << ans;
	}
	cout << '\n';
}
