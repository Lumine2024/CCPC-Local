#include "testlib.h"
#include <bits/stdc++.h>

using namespace std;

int main(int argc, char* argv[]) {
    registerGen(argc, argv, 1);
    if (argc != 3) {
        cerr << "Usage: generator <type> <seed>\n";
        return 1;
    }

    string type = argv[1];
    long long seed = atoll(argv[2]);
    rnd.setSeed(seed);

    if (type == "sample-1") {
        cout << "2 3\naa\n1 2 1\n1 2 2\n1 1 1\n";
        return 0;
    }
    if (type == "sample-2") {
        cout << "10 10\nddcbbbbbbc\n"
             << "2 7 2\n1 9 5\n1 8 7\n1 9 2\n3 8 2\n"
             << "2 8 1\n1 7 2\n1 10 5\n1 8 1\n1 10 10\n";
        return 0;
    }
    if (type == "min") {
        cout << "1 3\na\n1 1 1\n1 1 2\n1 1 1000000000\n";
        return 0;
    }
    int n, q;
    string s;
    if (type == "small") {
        n = rnd.next(2, 13);
        q = 100;
        s.resize(n);
        for (char& c : s) c = char('a' + rnd.next(0, 4));
    } else if (type == "uniform") {
        n = q = 100000;
        s = string(n - 1, 'a') + 'e';
    } else if (type == "alternating") {
        n = q = 100000;
        s.resize(n);
        for (int i = 0; i < n; ++i) s[i] = char('a' + i % 2);
    } else if (type == "random-large") {
        n = q = 100000;
        s.resize(n);
        for (char& c : s) c = char('a' + rnd.next(0, 4));
    } else if (type == "all-same") {
        n = q = 100000;
        s = string(n, 'a');
    } else {
        cerr << "Unknown case type: " << type << '\n';
        return 2;
    }
    cout << n << ' ' << q << '\n' << s << '\n';
    for (int i = 0; i < q; ++i) {
        int l, r, k;
        if (type == "small") {
            l = rnd.next(1, n);
            r = rnd.next(l, n);
            k = rnd.next(1, 1000);
        } else if (type == "uniform") {
            l = 1;
            r = n;
            k = i % 3 == 0 ? 1 : (i % 3 == 1 ? 100000 : 100001);
        } else if (type == "alternating") {
            l = 1;
            r = n;
            k = rnd.next(1, 1000000000);
        } else if (type == "all-same") {
            l = rnd.next(1, n);
            r = rnd.next(l, n);
            k = i % 3 == 0 ? 1 : rnd.next(1, 1000000000);
        } else {
            l = rnd.next(1, n);
            r = rnd.next(l, n);
            k = rnd.next(1, 1000000000);
        }
        cout << l << ' ' << r << ' ' << k << '\n';
    }
    return 0;
}
