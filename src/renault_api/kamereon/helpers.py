"""Helpers for Kamereon models."""

from __future__ import annotations

from typing import Any
from warnings import warn

from . import models

DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def update_schedule(schedule: models.ChargeSchedule, settings: dict[str, Any]) -> None:
    """Update charge schedule."""
    warn(
        "This method is deprecated, please use update_charge_schedule.",
        DeprecationWarning,
        stacklevel=2,
    )
    update_charge_schedule(schedule, settings)


def update_charge_schedule(
    schedule: models.ChargeSchedule, settings: dict[str, Any]
) -> None:
    """Update charge schedule."""
    if "activated" in settings:
        schedule.activated = settings["activated"]
    for day in DAYS_OF_WEEK:
        if day in settings:
            day_settings = settings[day]

            if day_settings is None:
                setattr(schedule, day, None)
            elif day_settings:
                start_time = day_settings["startTime"]
                duration = day_settings["duration"]

                setattr(
                    schedule,
                    day,
                    models.ChargeDaySchedule(day_settings, start_time, duration),
                )


def update_hvac_schedule(
    schedule: models.HvacSchedule, settings: dict[str, Any]
) -> None:
    """Update HVAC schedule."""
    if "activated" in settings:
        schedule.activated = settings["activated"]
    for day in DAYS_OF_WEEK:
        if day in settings:
            day_settings = settings[day]

            if day_settings is None:
                setattr(schedule, day, None)
            elif day_settings:
                ready_at_time = day_settings["readyAtTime"]

                setattr(
                    schedule,
                    day,
                    models.HvacDaySchedule(day_settings, ready_at_time),
                )


def create_schedule(
    settings: dict[str, Any],
) -> models.ChargeSchedule:
    warn(
        "This method is deprecated, please use create_charge_schedule.",
        DeprecationWarning,
        stacklevel=2,
    )
    return create_charge_schedule(settings)


def create_charge_schedule(
    settings: dict[str, Any],
) -> models.ChargeSchedule:
    """Create one schedule based in input. copy from dict."""
    schedule_id = settings.get("id")
    activated = bool(settings.get("activated"))
    schedule = models.ChargeSchedule(
        raw_data=settings,
        id=schedule_id,
        activated=activated,
        monday=None,
        tuesday=None,
        wednesday=None,
        thursday=None,
        friday=None,
        saturday=None,
        sunday=None,
    )
    # Copy day schedules details
    for day in DAYS_OF_WEEK:
        if day_data := settings.get(day):
            setattr(
                schedule,
                day,
                models.ChargeDaySchedule(
                    raw_data=day_data,
                    startTime=day_data.get("startTime"),
                    duration=day_data.get("duration"),
                ),
            )
    return schedule


def charge_schedule_from_kcm_settings(
    settings: dict[str, Any],
) -> models.ChargeSchedule:
    """Normalize a KCM `ev/settings` response into a ChargeSchedule.

    KCM-only vehicles (mode "kcm-settings") have no `charging-settings`
    endpoint; `get_charge_schedule()` returns this raw response instead.
    Its shape doesn't map onto ChargeSchedule field-for-field: it has one
    program per departure time with per-weekday boolean flags, rather than
    an independent start time and duration for each day. Only the first
    CHARGE-type program is used, since ChargeSchedule has no way to
    represent more than one time slot per week; `id` is synthesized as 1,
    since KCM programs carry none.

    `programDepartureTime` is a ready-by time, not a charge start time, and
    there's no reliable way to derive one from it (it depends on battery
    state). The response's own `chargeTimeStart`/`chargeDuration` already
    give the corresponding start and duration, so those are used directly
    instead of back-computing from the departure time.
    """
    charge_programs = [
        program
        for program in settings.get("programs") or []
        if program.get("programType") == "CHARGE"
    ]
    schedule = models.ChargeSchedule(
        raw_data=settings,
        id=1,
        activated=False,
        monday=None,
        tuesday=None,
        wednesday=None,
        thursday=None,
        friday=None,
        saturday=None,
        sunday=None,
    )
    if not charge_programs:
        return schedule

    program = charge_programs[0]
    schedule.activated = bool(program.get("programActivationStatus"))

    start_time = _kcm_time_to_charge_day_start(settings.get("chargeTimeStart"))
    duration = settings.get("chargeDuration")
    day_schedule = models.ChargeDaySchedule(
        raw_data=program, startTime=start_time, duration=duration
    )
    for day in DAYS_OF_WEEK:
        flag = f"programActivation{day.capitalize()}"
        if program.get(flag):
            setattr(schedule, day, day_schedule)

    return schedule


def _kcm_time_to_charge_day_start(hhmm: str | None) -> str | None:
    """Convert a KCM `HH:MM` time into ChargeDaySchedule's `Thh:mmZ` format."""
    if not hhmm:
        return None
    hours, minutes = hhmm.split(":")[:2]
    return f"T{int(hours):02d}:{int(minutes):02d}Z"


def create_hvac_schedule(
    settings: dict[str, Any],
) -> models.HvacSchedule:
    """Update schedule."""
    raise NotImplementedError


def get_end_time(start_time: str, duration: int | None = None) -> str:
    """Compute end time."""
    total_minutes = get_total_minutes(start_time, duration)
    return format_time(total_minutes)


def format_time(total_minutes: int) -> str:
    """Format time."""
    end_hours, end_minutes = divmod(total_minutes, 60)
    end_hours = end_hours % 24
    return f"T{end_hours:02g}:{end_minutes:02g}Z"


def get_total_minutes(start_time: str | None, duration: int | None = None) -> int:
    """Get total minutes from a `Thh:mmZ` formatted time."""
    if not start_time:
        return 0
    return int(start_time[1:3]) * 60 + int(start_time[4:6]) + (duration or 0)
