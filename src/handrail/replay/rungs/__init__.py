"""The ladder above the engine: three rungs, one file each, every rung asked once per page.

When the cook cannot tell which counter this is, the first thing to try is
cheap and bounded: ask a referee a closed question. "Which of these screens
is this: posted, already held, none of these?" The referee answers with a
probability per option. That is all the referee ever does.

Then the engine checks the call. A verdict is acted on only if the card's
threshold accepts it *and* the chosen screen's stored furniture overlaps what
is on the page by at least ``RECHECK``. A screen with no stored paths cannot
be re-checked, so a verdict for it is never acted on. Screen text is
untrusted and can steer a referee; the furniture cannot be talked into
anything.

Rung two sends a scout, a model with commit struck off its card, and checks
its report the same way. Rung three hands the baton to a person, whose word
is final but must still name a screen the run was hoping for. Every whistle
is a row in the episodes notebook, and the run's counters say which rungs
were climbed. On the ordinary path none of this is entered.
"""

from .one import RECHECK, RungOne
from .three import RungThree
from .two import RungTwo

__all__ = ["RECHECK", "RungOne", "RungThree", "RungTwo"]
