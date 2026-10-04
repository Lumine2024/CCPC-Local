#include <bits/stdc++.h>
using namespace std;
const long long P = 998244353;
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n;
	cin >> n;
	vector<int> a(n);
	for(auto &v : a) cin >> v;
	vector<long long> inv(200000 + 1);
	inv[1] = 1;
	for(int i = 2; i < (int)inv.size(); ++i)
		inv[i] = (P - P / i) * inv[P % i] % P;
	auto tri = [](long long x) { return x * (x + 1) / 2; };
	auto square_sum = [](long long x) { return x * (x + 1) * (2 * x + 1) / 6; };
	auto calc = [&](long long A, long long B) {
		long long t = min(A, B);
		// Sum (B-x)(B-x+1)/2 for x=1..t.
		long long sum_x = tri(t), sum_x2 = square_sum(t);
		long long S = (t * B * (B + 1) - (2 * B + 1) * sum_x + sum_x2) / 2;
		long long after = B * (B - 1) / 2;
		long long numerator =
			(after % P * ((A + B - 1) % P) + S % P - (A % P) * (after % P)) % P;
		if(numerator < 0) numerator += P;
		return numerator * inv[A + B - 1] % P;
	};
	for(int i = 0; i < n; i++) {
		if(i) cout << ' ';
		cout << (calc(a[i], a[(i + n - 1) % n]) + calc(a[i], a[(i + 1) % n])) %
					P;
	}
	cout << '\n';
}
