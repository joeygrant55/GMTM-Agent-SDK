"""Pure owner comparison tags, without identity disclosure or source access."""
import re

import pytest

from source_scope import owner_scope


def test_exact_actor_and_athlete_both_define_scope():
    value = owner_scope("sub_owner", 7201)
    assert re.fullmatch(r"[0-9a-f]{64}", value)
    assert value == owner_scope("sub_owner", 7201)
    assert len({value, owner_scope("sub_owner", 7202), owner_scope("other_owner", 7201),
                owner_scope("SUB_OWNER", 7201)}) == 4


@pytest.mark.parametrize("subject,athlete", [(None, 1), ("", 1), ("x" * 256, 1), ("x", True),
                                           ("x", "1"), ("x", 0), ("x", 9007199254740992)])
def test_invalid_owner_inputs_fail(subject, athlete):
    with pytest.raises(ValueError):
        owner_scope(subject, athlete)
