#include <bits/stdc++.h>
using namespace std;
using i64 = long long;

struct Node {
	i64 count = 0, sum = 0;
	bool clear = false;
};

class SegTree {
	int n;
	vector<Node> t;
	vector<int> value;
	void wipe(int p) {
		t[p] = Node{};
		t[p].clear = true;
	}
	void push(int p) {
		if(t[p].clear) {
			wipe(p * 2);
			wipe(p * 2 + 1);
			t[p].clear = false;
		}
	}
	void pull(int p) {
		t[p].count = t[p * 2].count + t[p * 2 + 1].count;
		t[p].sum = t[p * 2].sum + t[p * 2 + 1].sum;
	}
	void change(int p, int l, int r, int at, i64 delta) {
		if(l == r) {
			t[p].count += delta;
			t[p].sum += delta * value[l];
			return;
		}
		push(p);
		int mid = (l + r) / 2;
		if(at <= mid) change(p * 2, l, mid, at, delta);
		else change(p * 2 + 1, mid + 1, r, at, delta);
		pull(p);
	}
	void erase(int p, int l, int r, int ql, int qr) {
		if(ql > r || qr < l) return;
		if(ql <= l && r <= qr) {
			wipe(p);
			return;
		}
		push(p);
		int mid = (l + r) / 2;
		erase(p * 2, l, mid, ql, qr);
		erase(p * 2 + 1, mid + 1, r, ql, qr);
		pull(p);
	}
	Node query(int p, int l, int r, int ql, int qr) {
		if(ql > r || qr < l) return {};
		if(ql <= l && r <= qr) return t[p];
		push(p);
		int mid = (l + r) / 2;
		Node a = query(p * 2, l, mid, ql, qr);
		Node b = query(p * 2 + 1, mid + 1, r, ql, qr);
		return {a.count + b.count, a.sum + b.sum, false};
	}
	int kth(int p, int l, int r, i64 rank) {
		if(l == r) return l;
		push(p);
		int mid = (l + r) / 2;
		if(rank <= t[p * 2].count) return kth(p * 2, l, mid, rank);
		return kth(p * 2 + 1, mid + 1, r, rank - t[p * 2].count);
	}

public:
	explicit SegTree(vector<int> coords)
		: n((int)coords.size()), t(4 * n), value(move(coords)) {}
	void change(int at, i64 delta) {
		change(1, 0, n - 1, at, delta);
	}
	void erase(int l, int r) {
		if(l <= r) erase(1, 0, n - 1, l, r);
	}
	Node query(int l, int r) {
		return l <= r ? query(1, 0, n - 1, l, r) : Node{};
	}
	int kth(i64 rank) {
		return kth(1, 0, n - 1, rank);
	}
};

struct Op {
	int type, x, y;
	i64 k;
};
int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int q;
	cin >> q;
	vector<Op> ops(q);
	vector<int> coords = {-1, 0, 1};
	for(auto &o : ops) {
		cin >> o.type;
		if(o.type == 1) {
			cin >> o.x >> o.y;
			coords.push_back(o.y);
		} else cin >> o.k;
	}
	sort(coords.begin(), coords.end());
	coords.erase(unique(coords.begin(), coords.end()), coords.end());
	SegTree tree(coords);
	auto index = [&](int x) {
		return int(lower_bound(coords.begin(), coords.end(), x) -
				   coords.begin());
	};
	int minus = index(-1), zero = index(0), plus = index(1),
		last = (int)coords.size() - 1;
	for(auto o : ops) {
		if(o.type == 1) {
			tree.change(index(o.y), o.x);
			continue;
		}
		i64 already = o.type == 2 ? tree.query(plus, last).count
								  : tree.query(0, minus).count;
		i64 need = max(0LL, o.k - already);
		if(!need) {
			cout << 0 << '\n';
			continue;
		}
		i64 cost;
		if(o.type == 2) {
			i64 nonpositive = tree.query(0, zero).count;
			int boundary = tree.kth(nonpositive - need + 1);
			Node upper = tree.query(boundary + 1, zero);
			i64 partial = need - upper.count;
			i64 chosenSum = upper.sum + partial * coords[boundary];
			tree.erase(boundary + 1, zero);
			tree.change(boundary, -partial);
			tree.change(plus, need);
			cost = need - chosenSum;
		} else {
			i64 negatives = tree.query(0, minus).count;
			int boundary = tree.kth(negatives + need);
			Node lower = tree.query(zero, boundary - 1);
			i64 partial = need - lower.count;
			i64 chosenSum = lower.sum + partial * coords[boundary];
			tree.erase(zero, boundary - 1);
			tree.change(boundary, -partial);
			tree.change(minus, need);
			cost = need + chosenSum;
		}
		cout << cost << '\n';
	}
}
