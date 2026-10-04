#include <bits/stdc++.h>
using namespace std;
constexpr long long MOD = 1000000007;

// Incorrect: counts every distribution of m boxes among n columns.
int main() {
	int n, m;
	cin >> n >> m;
	for(int i = 0, value; i < n; ++i) cin >> value;
	vector<long long> factorial(n + m), inverse(n + m);
	factorial[0] = 1;
	for(int i = 1; i < n + m; ++i) factorial[i] = factorial[i - 1] * i % MOD;
	auto power = [](long long a, long long e) {
		long long result = 1;
		while(e) {
			if(e & 1) result = result * a % MOD;
			a = a * a % MOD;
			e >>= 1;
		}
		return result;
	};
	inverse[n + m - 1] = power(factorial[n + m - 1], MOD - 2);
	for(int i = n + m - 1; i > 0; --i) inverse[i - 1] = inverse[i] * i % MOD;
	cout << factorial[n + m - 1] * inverse[n - 1] % MOD * inverse[m] % MOD
		 << '\n';
}
