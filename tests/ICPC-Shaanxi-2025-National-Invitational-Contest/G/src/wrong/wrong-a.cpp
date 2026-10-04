#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m;
	string s;
	cin >> n >> m >> s;
	int c = count(s.begin(), s.end(), '1');
	cout << 1LL * m * max(c, n - c) << '\n';
}
