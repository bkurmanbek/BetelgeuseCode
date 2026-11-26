"""Real-looking keys for the scripts: made-up email addresses built from common first and last names.

    python3 code/people.py            # the first 10 of the addresses the scripts use
    python3 code/people.py 5          # the first 5

Standard library only, any Python 3.8+. Shared by count_compares.py and growth.py (not needed to run them by hand).

Each address pairs a common first name with a common last name at one of the big mail providers
(`maria.lopez@gmail.com`); a number goes on the end only when the same pair comes up again
(`maria.lopez7@outlook.com`). They look real but belong to no one we know of. The same seed gives the same
addresses on every machine, and the first n of a longer list are the same as a list of n.
"""

from __future__ import annotations

import random
import sys

FIRST = """emma olivia sophia mia isabella amelia ella grace chloe lily hannah sarah anna laura julia maria sofia lucia
elena carmen paula camila valentina gabriela daniela aigerim aliya madina zarina dinara amina fatima leila yasmin
nora ingrid freya astrid mei yuki hana minji priya ananya aisha zainab james john michael david daniel matthew
andrew ryan ethan noah liam lucas mason jacob william thomas oliver jack henry samuel benjamin alexander leon felix
jonas lukas paul marco luca matteo diego carlos javier pablo miguel mateo santiago arman timur daniyar aidar askar
omar ali hassan karim yusuf ivan dmitri kenji haruto minho wei jun raj arjun rohan kwame kofi tunde""".split()
LAST = """smith johnson williams brown jones miller davis wilson anderson taylor thomas moore martin jackson white
harris clark lewis walker hall young king wright scott green baker adams nelson hill campbell garcia rodriguez
martinez hernandez lopez gonzalez perez sanchez ramirez torres flores rivera gomez diaz morales ortiz castro silva
santos oliveira costa pereira rossi russo ferrari bianchi romano mueller schmidt schneider fischer weber meyer
wagner becker novak kowalski nowak ivanov petrov popov volkov kim lee park choi kang tanaka suzuki sato watanabe
wang zhang liu chen yang nguyen tran patel sharma singh kumar khan ahmed ibrahim mensah okafor adeyemi nurlanov
akhmetov omarov bekov suleimenov""".split()
DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com", "proton.me"]
WEIGHTS = [50, 12, 12, 10, 10, 6]
SEED = 2026
# Never generated (rosa is not in FIRST), so a lookup for it is a guaranteed miss.
NOBODY = "rosa.mendes@proton.me"


def emails(n: int, seed: int = SEED) -> list[str]:
    """n distinct addresses. Address i is name pair (i mod P) of a shuffled list of the P pairs, with the number
    i // P on the end when it isn't 0: distinct by construction, no set needed to check."""
    rng = random.Random(seed)
    pairs = [f"{f}.{l}" for f in FIRST for l in LAST]
    rng.shuffle(pairs)
    domains = rng.choices(DOMAINS, weights=WEIGHTS, k=n)
    p = len(pairs)
    return [f"{pairs[i % p]}{i // p or ''}@{domains[i]}" for i in range(n)]


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    print("\n".join(emails(n)))
