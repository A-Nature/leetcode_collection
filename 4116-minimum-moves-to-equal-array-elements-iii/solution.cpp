class Solution {
public:
    int minMoves(vector<int>& nums) {
        int moves = 0, max = nums[0];
        bool allEqual = false;

        for (int i = 0; i < nums.size(); i++){
            if (nums[i] > max) max = nums[i];
        }

        while (allEqual == false){
            allEqual = true;
            for (int i = 0; i < nums.size(); i++){
                if (nums[i] == max){
                    continue;
                }
                else{
                    nums[i]++;
                    moves++;
                    allEqual = false;
                }
            }
        }
        return moves;
    }
};
