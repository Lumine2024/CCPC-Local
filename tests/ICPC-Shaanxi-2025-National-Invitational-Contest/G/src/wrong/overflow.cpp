#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m;
	string s;
	cin >> n >> m >> s;
	int d = gcd(n, m);
	vector<array<int, 2>> c(d);
	for(int i = 0; i < n; i++) c[i % d][s[i] - '0']++;
	int a = 0;
	for(auto x : c) a += max(x[0], x[1]);
	cout << a * m << '\n';
}
