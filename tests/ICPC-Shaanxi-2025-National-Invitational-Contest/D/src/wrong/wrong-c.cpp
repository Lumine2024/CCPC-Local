#include <bits/stdc++.h>
using namespace std;

// Incorrect: handles exactly one filled valley, missing combinations of
// valleys.
int main() {
	int n, m;
	cin >> n >> m;
	vector<int> a(n + 2, 1000000000);
	for(int i = 1; i <= n; ++i) cin >> a[i];
	int answer = 0;
	for(int left = 0; left <= n; ++left) {
		int maximum = -1;
		long long sum = 0;
		for(int right = left + 2; right <= n + 1; ++right) {
			maximum = max(maximum, a[right - 1]);
			sum += a[right - 1];
			if(maximum >= a[left]) break;
			int length = right - left - 1;
			if((m + sum) % length) continue;
			long long height = (m + sum) / length;
			if(height > maximum && height <= min(a[left], a[right])) ++answer;
		}
	}
	cout << answer << '\n';
}
