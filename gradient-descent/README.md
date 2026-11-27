# How does a computer find the lowest point of a landscape it can't see?

Gradient descent from scratch: feel the slope, step against it, repeat. These materials go with the video lesson.
They start from a one-knob valley you can walk by hand, then cover the gradient on a two-knob landscape, the step size
and the exact number that decides it, and a computer fitting a line to apartment rents on its own. The code makes
every number: the walks run for real in plain Python, and the answers they are checked against come from exact
fractions. Nothing is timed.

```text
one knob, eta = 1/4               6 → 4 → 3 → 2.5 → 2.25             each step halves the distance to the bottom
step sizes 1/20, 1/4, 3/4         57, 9, 9 steps to within 0.01      distance × (1 − 2η) per step
step sizes 1 and 11/10            never: bounces forever, flies off
two knobs, eta = 0.6              25 steps to the deep valley (-0.866); 10 to the shallow one (-0.369) from another start
the landscape's step limit        2 / 2.163 = 0.9247; at eta = 1.4 it never settles
a line through 12 apartments      typical miss 603.8 → 132.9 euros in 40 steps, 0.46 from least squares
the same line, usual knobs        a valley 97,590× more curved one way: 738,888 steps
```

![Gradient descent on a landscape over two knobs: from one start the walk reaches the lowest point in 25 steps, from another it settles in a shallower valley in 10.](figures/walks.png)

## What's inside

| | |
|---|---|
| [`notes.pdf`](notes.pdf) | The handout: the slope and how it is felt, the rule by hand, the gradient and why it points uphill, two valleys, the step size and its limit 2/curvature, a line fitted to 12 apartments and why it tilts before it slides, the long thin valley of the usual knobs, Cauchy's note of 1847, where it stops working, common mistakes, exercises with answers, sources |
| [`notebook.ipynb`](notebook.ipynb) | Run it yourself: slopes from two heights, the walk in exact fractions, five step sizes plotted, the landscape with both walks and the bouncing one, a scan of step sizes across the limit, the line and its error bowl, the long thin valley; two "your turn" experiments |
| [`code/descent.py`](code/descent.py) | The video's four-line loop, exactly: prints 4.0, 3.0, 2.5, 2.25 |
| [`code/one_knob.py`](code/one_knob.py) | The slope felt from two heights, and the walk in exact fractions; `--eta`, `--start`, `--steps` |
| [`code/step_size.py`](code/step_size.py) | The five step sizes side by side and each walk drawn on a number line, step by step; `--eta` for your own |
| [`code/landscape.py`](code/landscape.py) | The two-knob landscape: the gradient, both walks, the bottoms and their curvatures, the step limit, the bouncing walk, and a text map; `--eta`, `--start`, `--plot` |
| [`code/rent_line.py`](code/rent_line.py) | The line through 12 apartments: the walk, the exact least-squares answer in fractions, why each knob moves as it does, and the same fit with the usual knobs (738,888 steps); `--plot` |
| [`figures/`](figures) | The pictures in the notes: stills from the video lesson, and five charts drawn from the runs |

## Run it

Python 3.9 or newer, standard library only (matplotlib optional, for `--plot` and the notebook's pictures). Every
script runs from the folder root or from `code/`, in well under a second unless noted.

```bash
python3 code/descent.py               # 1 4.0 / 2 3.0 / 3 2.5 / 4 2.25
python3 code/one_knob.py --eta 3/4    # the walk that overshoots and bounces in, in exact fractions
python3 code/step_size.py             # five step sizes, each walk drawn on a number line
python3 code/landscape.py             # the gradient, both walks, the step limit, text maps
python3 code/landscape.py --eta 0.93  # just past the limit: watch it keep bouncing
python3 code/rent_line.py             # the line, and the usual knobs' 738,888-step walk: about 2 s
python3 code/rent_line.py --quick     # the same without the long walk, instantly
```

## How the numbers were made

Nothing is timed. Every position, slope, height and step count comes from running the walks, with the same starts,
step sizes and stopping rules as the video. The one-knob walks use exact fractions; the landscape and the line use
ordinary floating point, and their best answers are checked against algebra: the landscape's bottoms are polished with
Newton's method and checked (slope zero, curving up both ways), and the line's best fit is computed in exact fractions
by least squares. The landscape is a made-up formula, written out in `code/landscape.py`. The 12 apartments
are made up too: generated from a fixed seed (1847) around a believable Lisbon price per square metre, not
real listings.

The history is cited, not computed: Augustin-Louis Cauchy's note in the Comptes rendus of 1847,
Claude Lemaréchal's account of it (2012), and the GPT-3 paper (2020) for "billions of knobs", each linked in the notes.

Found a mistake, or a number you can't reproduce? Open an issue with the script's output and your Python version.

## About

Part of a series of short lessons that show what happens under the hood: a video, these notes, a notebook and the
code that makes every number from a real run.

Made by Bakytzhan Kurmanbek.

More lessons: [bkurmanbek on GitHub](https://github.com/bkurmanbek).

Ideas for a lesson, a collaboration or a project? bakytzhan.kurmanbek@nu.edu.kz
