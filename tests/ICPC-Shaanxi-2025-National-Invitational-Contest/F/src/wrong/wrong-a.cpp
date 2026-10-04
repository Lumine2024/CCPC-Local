#include <bits/stdc++.h>
using namespace std;
const long long P = 998244353;
long long c3(long long x) {
	return x * (x - 1) * (x - 2) / 6;
}
long long power(long long a, long long b) {
	long long r = 1;
	for(; b; b >>= 1, a = a * a % P)
		if(b & 1) r = r * a % P;
	return r;
}
int main() {
	int n;
	cin >> n;
	vector<int> a(n);
	for(int &x : a) cin >> x;
	auto f = [&](int A, int B) {
		int t = min(A, B);
		long long S = c3(B + 1) - c3(B - t + 1);
		return S % P * power(A + B - 1, P - 2) % P;
	};
	for(int i = 0; i < n; i++)
		cout << (f(a[i], a[(i + n - 1) % n]) + f(a[i], a[(i + 1) % n])) % P
			 << (i + 1 == n ? '\n' : ' ');
}
