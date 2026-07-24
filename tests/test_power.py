"""``factory on`` / ``factory off`` — the process-level kill switch.

Must be idempotent and correct from ANY starting state (active, inactive,
disabled, failed, half-up), and must shut down CLEANLY: timers first so no new
work starts, then drain an in-flight tick, then the daemons.

``systemctl`` is injected so these tests never touch real units.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from factory.power import (
    discover_units,
    power_off,
    power_on,
    power_status,
    unit_state,
)

_INSTALLED = (
    "factory-tick@.timer\nfactory-tick@.service\nfactory-manager.service\n"
    "factory-self-deploy.timer\nsacrifice-redeploy-main.timer\n"
)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for app in ("sacrifice", "factory"):
        d = tmp_path / "apps" / app
        d.mkdir(parents=True)
        (d / "config.yaml").write_text("name: x\nrepo: a/b\n", encoding="utf-8")
    return tmp_path


class FakeSystemctl:
    """Records every systemctl invocation and serves scripted states."""

    def __init__(
        self,
        *,
        active: dict[str, str] | None = None,
        enabled: dict[str, str] | None = None,
        running_ticks: list[str] | None = None,
        unit_files: str = _INSTALLED,
        start_fails: set[str] | None = None,
    ) -> None:
        self.calls: list[list[str]] = []
        self.active = active or {}
        self.enabled = enabled or {}
        self.running_ticks = list(running_ticks or [])
        self.unit_files = unit_files
        self.start_fails = start_fails or set()

    def __call__(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        args = cmd[2:]  # strip ["systemctl", "--user"]
        verb = args[0] if args else ""
        target = args[1] if len(args) > 1 else ""

        if verb == "list-unit-files":
            return self._ok(self.unit_files)
        if verb == "list-units":
            return self._ok("\n".join(f"{t} loaded active running x" for t in self.running_ticks))
        if verb == "is-active":
            return self._ok(self.active.get(target, "inactive"))
        if verb == "is-enabled":
            if target in self.enabled:
                return self._ok(self.enabled[target])
            # Real systemctl reports ``not-found`` (exit 4) for a unit it does not
            # know about — model that, so ``UnitState.installed`` is exercised
            # faithfully rather than every unknown unit looking merely disabled.
            return self._ok("disabled" if self._is_installed(target) else "not-found")
        if verb == "stop":
            self.active[target] = "inactive"
            self.running_ticks = [t for t in self.running_ticks if t != target]
            return self._ok("")
        if verb == "disable":
            self.enabled[target] = "disabled"
            return self._ok("")
        if verb == "enable":
            self.enabled[target] = "enabled"
            return self._ok("")
        if verb == "start":
            if target in self.start_fails:
                return subprocess.CompletedProcess(cmd, 1, "", f"{target} boom")
            self.active[target] = "active"
            return self._ok("")
        if verb == "reset-failed":
            if self.active.get(target) == "failed":
                self.active[target] = "inactive"
            return self._ok("")
        return self._ok("")

    def _is_installed(self, unit: str) -> bool:
        """Mirror systemd's template rule: ``foo@bar.service`` ← ``foo@.service``."""
        names = set(self.unit_files.split())
        if unit in names:
            return True
        if "@" in unit:
            base, _, suffix = unit.partition("@")
            return f"{base}@.{suffix.rsplit('.', 1)[-1]}" in names
        return False

    @staticmethod
    def _ok(out: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["x"], 0, out, "")

    def verbs_for(self, unit: str) -> list[str]:
        return [c[2] for c in self.calls if len(c) > 3 and c[3] == unit]

    def order_of(self, verb: str) -> list[str]:
        return [c[3] for c in self.calls if len(c) > 3 and c[2] == verb]


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #


def test_discovers_per_app_and_global_units(root: Path) -> None:
    fake = FakeSystemctl()
    names = {u.name for u in discover_units(root=root, runner=fake)}
    assert "factory-tick@sacrifice.timer" in names
    assert "factory-tick@factory.timer" in names, "per-app units come from apps/*/config.yaml"
    assert "factory-manager.service" in names
    assert "factory-self-deploy.timer" in names
    assert "sacrifice-redeploy-main.timer" in names


def test_uninstalled_units_are_skipped(root: Path) -> None:
    """A machine without the manager unit must not error on it."""
    fake = FakeSystemctl(unit_files="factory-tick@.timer\n")
    names = {u.name for u in discover_units(root=root, runner=fake)}
    assert names == {"factory-tick@sacrifice.timer", "factory-tick@factory.timer"}


def test_no_units_installed_is_not_an_error(tmp_path: Path) -> None:
    fake = FakeSystemctl(unit_files="")
    assert discover_units(root=tmp_path, runner=fake) == []
    assert power_status(root=tmp_path, runner=fake) == []


# --------------------------------------------------------------------------- #
# off
# --------------------------------------------------------------------------- #


def test_off_stops_timers_before_services(root: Path) -> None:
    """Order is the whole point: no new work may start while we drain."""
    fake = FakeSystemctl(active={"factory-manager.service": "active"})
    power_off(root=root, runner=fake, wait=False)

    stops = fake.order_of("stop")
    assert "factory-manager.service" in stops
    manager_at = stops.index("factory-manager.service")
    timer_idxs = [i for i, n in enumerate(stops) if n.endswith(".timer")]
    assert timer_idxs, "timers should have been stopped"
    assert max(timer_idxs) < manager_at, "every timer must stop before the daemon"


def test_off_is_idempotent_when_already_off(root: Path) -> None:
    fake = FakeSystemctl()
    report = power_off(root=root, runner=fake, wait=False)
    assert report["already_off"] is True
    assert not [s for s in report["units"] if s.running]


def test_off_clears_sticky_failed_state(root: Path) -> None:
    """A unit left ``failed`` must read ``inactive`` afterwards, not ``failed``."""
    fake = FakeSystemctl(active={"factory-manager.service": "failed"})
    report = power_off(root=root, runner=fake, wait=False)
    assert "reset-failed" in fake.verbs_for("factory-manager.service")
    states = {s.name: s.active for s in report["units"]}
    assert states["factory-manager.service"] == "inactive"


def test_off_waits_for_inflight_tick_then_confirms_stopped(root: Path) -> None:
    fake = FakeSystemctl(running_ticks=["factory-tick@sacrifice.service"])
    slept: list[float] = []

    def _sleep(s: float) -> None:
        slept.append(s)
        fake.running_ticks = []  # the tick finishes on its own

    report = power_off(root=root, runner=fake, wait=True, sleep=_sleep)

    assert slept, "should have waited for the in-flight tick"
    assert report["drained"] == ["factory-tick@sacrifice.service"]
    assert report["drain_timed_out"] is False


def test_off_now_does_not_wait_but_still_stops_the_tick(root: Path) -> None:
    fake = FakeSystemctl(running_ticks=["factory-tick@sacrifice.service"])
    slept: list[float] = []
    report = power_off(root=root, runner=fake, wait=False, sleep=lambda s: slept.append(s))

    assert slept == [], "--now must not wait"
    assert "factory-tick@sacrifice.service" in fake.order_of("stop")
    assert report["drained"] == []


def test_off_reports_drain_timeout_and_stops_anyway(root: Path) -> None:
    """A tick that never finishes must not hang the command forever."""
    fake = FakeSystemctl(running_ticks=["factory-tick@sacrifice.service"])
    report = power_off(
        root=root, runner=fake, wait=True, drain_timeout_s=4, sleep=lambda _s: None
    )
    assert report["drain_timed_out"] is True
    assert "factory-tick@sacrifice.service" in fake.order_of("stop")
    assert not [s for s in report["units"] if s.running]


def test_off_disables_so_a_reboot_does_not_restart_it(root: Path) -> None:
    fake = FakeSystemctl(enabled={"factory-tick@sacrifice.timer": "enabled"})
    report = power_off(root=root, runner=fake, wait=False)
    assert "disable" in fake.verbs_for("factory-tick@sacrifice.timer")
    assert all(s.enabled != "enabled" for s in report["units"])


# --------------------------------------------------------------------------- #
# on
# --------------------------------------------------------------------------- #


def test_on_starts_services_before_timers(root: Path) -> None:
    """The manager should be watching before the ticks that feed it."""
    fake = FakeSystemctl()
    power_on(root=root, runner=fake)

    starts = fake.order_of("start")
    assert "factory-manager.service" in starts
    svc_at = starts.index("factory-manager.service")
    timer_idxs = [i for i, n in enumerate(starts) if n.endswith(".timer")]
    assert min(timer_idxs) > svc_at


def test_on_recovers_from_failed_state(root: Path) -> None:
    """The 'it won't come back up' case: a failed unit must still start."""
    fake = FakeSystemctl(active={"factory-manager.service": "failed"})
    report = power_on(root=root, runner=fake)

    verbs = fake.verbs_for("factory-manager.service")
    assert verbs.index("reset-failed") < verbs.index("start"), "must clear failure BEFORE starting"
    assert report["failed"] == []
    assert all(s.running for s in report["units"])


def test_on_is_idempotent_when_already_on(root: Path) -> None:
    fake = FakeSystemctl(
        active={
            "factory-manager.service": "active",
            "factory-tick@sacrifice.timer": "active",
            "factory-tick@factory.timer": "active",
            "factory-self-deploy.timer": "active",
            "sacrifice-redeploy-main.timer": "active",
        }
    )
    report = power_on(root=root, runner=fake)
    assert report["already_on"] is True
    assert all(s.running for s in report["units"])


def test_on_reports_a_unit_that_refuses_to_start(root: Path) -> None:
    fake = FakeSystemctl(start_fails={"factory-manager.service"})
    report = power_on(root=root, runner=fake)
    assert [n for n, _ in report["failed"]] == ["factory-manager.service"]
    assert "boom" in report["failed"][0][1]


def test_off_then_on_round_trips(root: Path) -> None:
    fake = FakeSystemctl(
        active={"factory-manager.service": "active", "factory-tick@sacrifice.timer": "active"}
    )
    off = power_off(root=root, runner=fake, wait=False)
    assert not [s for s in off["units"] if s.running]

    on = power_on(root=root, runner=fake)
    assert on["failed"] == []
    assert all(s.running for s in on["units"])
    assert all(s.enabled == "enabled" for s in on["units"])


def test_half_up_state_is_visible(root: Path) -> None:
    fake = FakeSystemctl(active={"factory-manager.service": "active"})
    states = power_status(root=root, runner=fake)
    running = [s for s in states if s.running]
    assert len(running) == 1 and len(states) > 1, "half-up must be distinguishable from on/off"


def test_unit_state_never_raises_on_unknown_unit(root: Path) -> None:
    fake = FakeSystemctl(enabled={}, active={})
    st = unit_state("does-not-exist.service", runner=fake)
    assert st.installed is False
    assert st.running is False
