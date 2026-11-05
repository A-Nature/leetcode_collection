class Solution {
public:
    double myPow(double x, int n) {
        double power = 1;
        bool isNegative = false;
        long long exp = n;

        if (n < 0){
            isNegative = true;
            exp *= -1;
        }

        while (exp > 0){
            if (exp % 2 == 1) power *= x;
            x *= x;
            exp /= 2;
        }

        if (isNegative) power = 1.0 / power;

        return power;
    }
};
