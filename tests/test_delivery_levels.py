import pytest

from factory.delivery import DeliveryConfig, effective_level
from factory.delivery import DeliveryLevel as L


def test_absent_block_keeps_legacy_auto_merge():
    assert effective_level(None) is L.AUTO_MERGE
    assert effective_level(DeliveryConfig()) is L.AUTO_MERGE


def test_request_can_lower_but_never_raise():
    cfg = DeliveryConfig(max=L.PR, default=L.DRAFT_PR)
    assert effective_level(cfg) is L.DRAFT_PR
    assert effective_level(cfg, "branch") is L.BRANCH
    assert effective_level(cfg, "push_to_main") is L.PR
    assert effective_level(cfg, "AUTO_MERGE") is L.PR


def test_garbage_request_fails_safe_to_none():
    assert effective_level(DeliveryConfig(), "merge-please") is L.NONE


def test_default_above_max_rejected():
    with pytest.raises(ValueError):
        DeliveryConfig(max=L.DRAFT_PR, default=L.AUTO_MERGE)


def test_predicates():
    assert not L.NONE.pushes and L.BRANCH.pushes
    assert L.DRAFT_PR.opens_pr and not L.BRANCH.opens_pr and not L.PUSH_TO_MAIN.opens_pr
    assert L.AUTO_MERGE.merges and L.PUSH_TO_MAIN.merges and not L.PR.merges
