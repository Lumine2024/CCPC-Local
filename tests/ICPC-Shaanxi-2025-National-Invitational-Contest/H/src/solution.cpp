#include <bits/stdc++.h>
using namespace std;

// All counts may be saturated because query ranks do not exceed 1e9.
static constexpr uint32_t CAP = 1000000001U;
using Row = array<uint32_t, 6>;
using Matrix = array<Row, 6>;

static uint32_t addcap(uint32_t x, uint32_t y) {
	return uint32_t(min<uint64_t>(CAP, uint64_t(x) + y));
}
static uint32_t mulcap(uint32_t x, uint32_t y) {
	return uint32_t(min<uint64_t>(CAP, uint64_t(x) * y));
}
static Row rowtimes(const Row &row, const Matrix &matrix) {
	Row result{};
	for(int i = 0; i < 6; ++i)
		for(int j = 0; j < 6; ++j)
			result[j] = addcap(result[j], mulcap(row[i], matrix[i][j]));
	return result;
}
static Row applyMatrix(const Matrix &matrix, const Row &vector) {
	Row result{};
	for(int i = 0; i < 6; ++i)
		for(int j = 0; j < 6; ++j)
			result[i] = addcap(result[i], mulcap(matrix[i][j], vector[j]));
	return result;
}
static uint32_t dot(const Row &x, const Row &y) {
	uint32_t result = 0;
	for(int i = 0; i < 6; ++i) result = addcap(result, mulcap(x[i], y[i]));
	return result;
}

struct Node {
	Matrix transform{};
	array<Row, 5>
		skipped{}; // Sum of smaller-character branches just after each c.
	array<Row, 5> skippedExceptLast{};
	array<Row, 5> lowerAfterLast{};
	array<Row, 5> lastCount{}; // F(position after the last c in this interval).
	array<int, 5> occurrences{};
	array<int, 5> lastPosition{};
};

class SegmentTree {
public:
	explicit SegmentTree(const string &s) {
		size_ = 1;
		while(size_ < int(s.size())) size_ <<= 1;
		tree_.resize(size_ * 2);
		for(int i = 0; i < size_; ++i) {
			Node &node = tree_[size_ + i];
			for(int j = 0; j < 6; ++j) node.transform[j][j] = 1;
			if(i >= int(s.size())) continue;
			int c = s[i] - 'a';
			node.transform[c].fill(1);
			for(int d = 0; d < c; ++d) node.skipped[c][d] = 1;
			node.lowerAfterLast[c] = node.skipped[c];
			node.lastCount[c].fill(1);
			node.occurrences[c] = 1;
			node.lastPosition[c] = i;
		}
		for(int i = size_ - 1; i; --i) {
			const Node &left = tree_[i * 2];
			const Node &right = tree_[i * 2 + 1];
			Node &node = tree_[i];
			for(int r = 0; r < 6; ++r)
				node.transform[r] =
					rowtimes(left.transform[r], right.transform);
			for(int c = 0; c < 5; ++c) {
				node.occurrences[c] =
					left.occurrences[c] + right.occurrences[c];
				node.lastPosition[c] = right.occurrences[c]
										   ? right.lastPosition[c]
										   : left.lastPosition[c];
				Row earlier = rowtimes(left.skipped[c], right.transform);
				for(int j = 0; j < 6; ++j)
					node.skipped[c][j] =
						addcap(earlier[j], right.skipped[c][j]);
				node.skippedExceptLast[c] =
					right.occurrences[c]
						? earlier
						: rowtimes(left.skippedExceptLast[c], right.transform);
				if(right.occurrences[c]) {
					for(int j = 0; j < 6; ++j)
						node.skippedExceptLast[c][j] =
							addcap(node.skippedExceptLast[c][j],
								   right.skippedExceptLast[c][j]);
				}
				node.lowerAfterLast[c] =
					right.occurrences[c]
						? right.lowerAfterLast[c]
						: rowtimes(left.lowerAfterLast[c], right.transform);
				node.lastCount[c] =
					right.occurrences[c]
						? right.lastCount[c]
						: rowtimes(left.lastCount[c], right.transform);
			}
		}
	}

	struct Block {
		int index;
		Row after;
	};
	struct Range {
		vector<Block> blocks;
		Row before;
	};
	Range query(int left, int right) const { // [left, right)
		vector<int> front, back;
		for(left += size_, right += size_; left < right;
			left >>= 1, right >>= 1) {
			if(left & 1) front.push_back(left++);
			if(right & 1) back.push_back(--right);
		}
		for(auto it = back.rbegin(); it != back.rend(); ++it)
			front.push_back(*it);
		Range result;
		result.blocks.resize(front.size());
		Row state{};
		state[5] = 1;
		for(int i = int(front.size()) - 1; i >= 0; --i) {
			result.blocks[i] = {front[i], state};
			state = applyMatrix(tree_[front[i]].transform, state);
		}
		result.before = state;
		return result;
	}

	struct Run {
		int count = 0, last = -1;
		uint32_t deducted = 0, lowerAfterLast = 0;
	};
	Run longestRun(const Range &range, int c, int tail, uint32_t rank) const {
		Run answer;
		for(int d = 0; d < c; ++d)
			answer.lowerAfterLast =
				addcap(answer.lowerAfterLast, range.before[d]);
		for(const Block &block : range.blocks) {
			if(!tree_[block.index].occurrences[c]) continue;
			if(canConsume(block.index, block.after, c, tail, rank, answer)) {
				consume(block.index, block.after, c, tail, answer);
			} else {
				descend(block.index, block.after, c, tail, rank, answer);
				break;
			}
		}
		return answer;
	}

private:
	uint32_t increment(int index, const Row &after, int c, int tail) const {
		const Node &node = tree_[index];
		uint32_t result = dot(node.skippedExceptLast[c], after);
		if(tail <= c) result = addcap(result, node.occurrences[c]);
		return result;
	}
	bool canConsume(int index, const Row &after, int c, int tail, uint32_t rank,
					const Run &current) const {
		uint32_t deduction = addcap(current.deducted, current.lowerAfterLast);
		deduction = addcap(deduction, increment(index, after, c, tail));
		uint32_t remaining = dot(tree_[index].lastCount[c], after);
		return deduction < rank && rank <= addcap(deduction, remaining);
	}
	void consume(int index, const Row &after, int c, int tail,
				 Run &current) const {
		const Node &node = tree_[index];
		current.deducted = addcap(current.deducted, current.lowerAfterLast);
		current.deducted =
			addcap(current.deducted, increment(index, after, c, tail));
		current.lowerAfterLast = dot(node.lowerAfterLast[c], after);
		current.count += node.occurrences[c];
		current.last = node.lastPosition[c];
	}
	void descend(int index, const Row &after, int c, int tail, uint32_t rank,
				 Run &current) const {
		if(index >= size_) return;
		int left = index * 2, right = left + 1;
		Row afterLeft = applyMatrix(tree_[right].transform, after);
		if(tree_[left].occurrences[c]) {
			if(canConsume(left, afterLeft, c, tail, rank, current))
				consume(left, afterLeft, c, tail, current);
			else {
				descend(left, afterLeft, c, tail, rank, current);
				return;
			}
		}
		if(!tree_[right].occurrences[c]) return;
		if(canConsume(right, after, c, tail, rank, current))
			consume(right, after, c, tail, current);
		else descend(right, after, c, tail, rank, current);
	}

	int size_;
	vector<Node> tree_;
};

int main() {
	ios::sync_with_stdio(false);
	cin.tie(nullptr);
	int n, q;
	string s;
	cin >> n >> q >> s;
	SegmentTree tree(s);
	vector<uint32_t> power(n + 1), repeat(n + 1);
	power[0] = 1;
	for(int i = 1; i <= n; ++i) {
		power[i] = power[i - 1] * 1331U;
		repeat[i] = repeat[i - 1] * 1331U + 1U;
	}
	while(q--) {
		int left, right;
		uint32_t rank;
		cin >> left >> right >> rank;
		--left;
		--right;
		if(left == right) {
			cout << -1 << '\n';
			continue;
		}
		int tail = s[right] - 'a', position = left + 1;
		uint32_t hash = uint32_t(s[left] - 'a' + 1);
		while(true) {
			auto range = tree.query(position, right);
			int choice = -1;
			uint32_t localRank = rank;
			for(int c = 0; c < 5; ++c) {
				uint32_t branch = addcap(range.before[c], uint32_t(c == tail));
				if(localRank > branch) localRank -= branch;
				else {
					choice = c;
					break;
				}
			}
			if(choice < 0) {
				cout << -1 << '\n';
				break;
			}
			auto run = tree.longestRun(range, choice, tail, rank);
			if(run.count == 0) {
				cout << (hash * 1331U + uint32_t(tail + 1)) << '\n';
				break;
			}
			hash = hash * power[run.count] +
				   uint32_t(choice + 1) * repeat[run.count];
			rank -= run.deducted;
			position = run.last + 1;
		}
	}
}
