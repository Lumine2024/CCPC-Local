#include <bits/stdc++.h>
using namespace std;
int main() {
	int n, m;
	string s;
	cin >> n >> m >> s;
	cout << 1LL * m * count(s.begin(), s.end(), '1') << '\n';
}
