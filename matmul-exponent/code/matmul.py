"""Multiply two 2 x 2 tables the school way and count the multiplications: each entry of the answer is one row
of the first table against one column of the second, so 2 x 2 entries x 2 products each = 8.

    python3 matmul.py          # prints the answer and the count, instantly

Exactly the code shown in the clips (part 1), so it prints exactly what their result pane shows:
    [[14, 8], [17, 9]]
    multiplications: 8

The tables: Emma orders two coffees and one tea, Liam one coffee and three teas (orders); a coffee costs 5 dollars
in Austin and 3 in Lima, a tea 4 and 2 (prices). answer[i][j] is what person i pays in city j. The three loops are
the three directions of the "cube of products": person (i), city (j), item (k). Change 2 to n and the same three
loops do n * n * n multiplications. Standard library only (nothing to import).
"""

orders = [[2, 1], [1, 3]]   # Emma, Liam
prices = [[5, 3], [4, 2]]   # coffee, tea
answer = [[0, 0], [0, 0]]
count = 0
for i in range(2):          # person
    for j in range(2):      # city
        for k in range(2):  # item
            answer[i][j] += orders[i][k] * prices[k][j]
            count += 1
print(answer)
print("multiplications:", count)
