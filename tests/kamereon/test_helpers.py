"""Tests for Kamereon helpers."""

from typing import Any

from renault_api.kamereon.helpers import charge_schedule_from_kcm_settings


def _kcm_settings(**overrides: Any) -> dict[str, Any]:
    """Build a synthetic KCM `ev/settings` response."""
    settings: dict[str, Any] = {
        "chargeModeRq": "SCHEDULED",
        "chargeTimeStart": "11:00",
        "chargeDuration": 510,
        "programs": [
            {
                "programActivationStatus": True,
                "programType": "CHARGE",
                "programDepartureTime": "19:30:00",
                "programActivationMonday": True,
                "programActivationTuesday": True,
                "programActivationWednesday": True,
                "programActivationThursday": True,
                "programActivationFriday": True,
                "programActivationSaturday": True,
                "programActivationSunday": True,
            }
        ],
    }
    settings.update(overrides)
    return settings


def test_charge_schedule_from_kcm_settings_full_week() -> None:
    """A single program active every day maps to a schedule for every day."""
    schedule = charge_schedule_from_kcm_settings(_kcm_settings())

    assert schedule.id == 1
    assert schedule.activated is True
    for day in (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ):
        day_schedule = getattr(schedule, day)
        assert day_schedule is not None
        assert day_schedule.startTime == "T11:00Z"
        assert day_schedule.duration == 510


def test_charge_schedule_from_kcm_settings_start_time_source() -> None:
    """The day's startTime comes from chargeTimeStart, not programDepartureTime."""
    schedule = charge_schedule_from_kcm_settings(
        _kcm_settings(chargeTimeStart="22:15", programDepartureTime="06:00:00")
    )

    assert schedule.monday is not None
    assert schedule.monday.startTime == "T22:15Z"


def test_charge_schedule_from_kcm_settings_partial_week() -> None:
    """Only the weekdays flagged on the program get a day schedule."""
    settings = _kcm_settings()
    settings["programs"][0]["programActivationTuesday"] = False
    settings["programs"][0]["programActivationThursday"] = False

    schedule = charge_schedule_from_kcm_settings(settings)

    assert schedule.monday is not None
    assert schedule.tuesday is None
    assert schedule.wednesday is not None
    assert schedule.thursday is None


def test_charge_schedule_from_kcm_settings_inactive_program() -> None:
    """An inactive program is reported as an unactivated schedule."""
    settings = _kcm_settings()
    settings["programs"][0]["programActivationStatus"] = False

    schedule = charge_schedule_from_kcm_settings(settings)

    assert schedule.activated is False
    # Days are still populated; only the whole-schedule flag reflects
    # inactivity, matching how the KCA model treats a disabled schedule.
    assert schedule.monday is not None


def test_charge_schedule_from_kcm_settings_ignores_non_charge_programs() -> None:
    """A non-CHARGE program (e.g. preconditioning) is not mistaken for one."""
    settings = _kcm_settings()
    settings["programs"][0]["programType"] = "PRECONDITIONING"

    schedule = charge_schedule_from_kcm_settings(settings)

    assert schedule.activated is False
    for day in (
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ):
        assert getattr(schedule, day) is None


def test_charge_schedule_from_kcm_settings_no_programs() -> None:
    """No programs at all yields an empty, unactivated schedule."""
    schedule = charge_schedule_from_kcm_settings(_kcm_settings(programs=[]))

    assert schedule.id == 1
    assert schedule.activated is False
    assert schedule.monday is None
