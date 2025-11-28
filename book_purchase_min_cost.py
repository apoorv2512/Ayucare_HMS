from functools import lru_cache

def min_cost_to_buy_books(costs, pairCost, k):
    n = len(costs)

    @lru_cache(None)
    def dp(left, right, pairs_used):
        if left > right:
            return 0
        # Option 1: Buy left book alone
        cost_left = costs[left] + dp(left + 1, right, pairs_used)
        # Option 2: Buy right book alone
        cost_right = costs[right] + dp(left, right - 1, pairs_used)
        # Option 3: Buy both left and right books together if pairs_used < k
        cost_pair = float('inf')
        if pairs_used < k and left < right:
            cost_pair = pairCost + dp(left + 1, right - 1, pairs_used + 1)
        return min(cost_left, cost_right, cost_pair)

    return dp(0, n - 1, 0)

if __name__ == "__main__":
    # Example usage
    costs = [10, 20, 30, 40, 50]
    pairCost = 25
    k = 2
    result = min_cost_to_buy_books(costs, pairCost, k)
    print(f"Minimum cost to buy all books: {result}")
