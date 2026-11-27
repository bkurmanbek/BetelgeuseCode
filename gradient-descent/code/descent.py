"""Gradient descent on one knob, in four lines: the exact program from the video's sandbox (chapter 2).

    python3 descent.py        # prints four positions, instantly

The valley is height = (x - 2)**2 + 1, so its slope at x is 2 * (x - 2) and its bottom is at x = 2. The walk starts
at x = 6 with step size eta = 0.25 (one quarter). Each turn of the loop measures the slope where it stands, steps
against it (new = old - eta * slope), and prints where it is now:

    1 4.0
    2 3.0
    3 2.5
    4 2.25

Each step is half the one before, because the slope halves as the distance to the bottom halves. Change eta to
0.05, 0.75, 1 or 1.1 and run it again (step_size.py does that for you). Standard library only (nothing to import).
"""

x, eta = 6, 0.25
for step in range(1, 5):
    slope = 2 * (x - 2)
    x = x - eta * slope
    print(step, x)
