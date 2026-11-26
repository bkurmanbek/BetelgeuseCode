"""Strassen's 1969 recipe on the same 2 x 2 tables: seven products m1 ... m7, each a sum or difference of entries
times a sum or difference of entries, then only additions and subtractions. Same answer as the school way's eight
products, with seven.

    python3 strassen.py        # prints the answer and the count, instantly

Exactly the code shown in the clips (part 2), so it prints exactly what their result pane shows:
    [[14, 8], [17, 9]]
    multiplications: 7

The 7 on the last line is the number of `*` in the seven lines above it: count them. blocks.py counts it for you
by running the recipe on numbers that tally their own multiplications, and applies it to blocks inside blocks.
The values here: m1 .. m7 = 35, 20, 2, -3, 6, -8, -12. Standard library only (nothing to import).
"""

a11, a12, a21, a22 = 2, 1, 1, 3   # orders
b11, b12, b21, b22 = 5, 3, 4, 2   # prices
m1 = (a11 + a22) * (b11 + b22)
m2 = (a21 + a22) * b11
m3 = a11 * (b12 - b22)
m4 = a22 * (b21 - b11)
m5 = (a11 + a12) * b22
m6 = (a21 - a11) * (b11 + b12)
m7 = (a12 - a22) * (b21 + b22)
print([[m1 + m4 - m5 + m7, m3 + m5],
       [m2 + m4, m1 - m2 + m3 + m6]])
print("multiplications:", 7)
