from handrail.schema.effects import MUTATING, Effect, EffectClass


def test_reads_and_navigation_do_not_mutate():
    assert not Effect(kind=EffectClass.READ).is_mutating
    assert not Effect(kind=EffectClass.NAVIGATE).is_mutating
    assert MUTATING == {EffectClass.STAGE, EffectClass.COMMIT}


def test_a_commit_without_a_probe_is_never_retryable():
    assert Effect(kind=EffectClass.COMMIT).is_retryable is False
    assert Effect(kind=EffectClass.COMMIT, probe="hold_exists").is_retryable is True


def test_everything_short_of_a_commit_is_retryable():
    for kind in (EffectClass.READ, EffectClass.NAVIGATE, EffectClass.STAGE):
        assert Effect(kind=kind).is_retryable is True
