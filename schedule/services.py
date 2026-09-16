import calendar
import datetime as dt
from collections import defaultdict

from .models import ScheduleEntry

DAY_START_HOUR = 10
DAY_END_HOUR = 21
DAY_SPAN_HOURS = DAY_END_HOUR - DAY_START_HOUR


def month_weeks(anchor: dt.date):
    """Full calendar weeks (Mon..Sun) covering the month of `anchor`."""
    cal = calendar.Calendar(firstweekday=0)
    return cal.monthdatescalendar(anchor.year, anchor.month)


def can_modify(entry, viewer):
    """Whether `viewer` may edit or delete this entry — same rule for both.

    The Academy's own bookings belong to management; a teacher's proposal
    belongs to the teacher who wrote it, and only while nobody has reviewed it
    yet — once accepted or rejected it is part of the record.

    Roles add up rather than pick a branch: somebody who both manages and
    teaches keeps the Academy bookings *and* their own proposals.
    """
    if viewer.is_super_admin:
        return True
    if viewer.is_manager and entry.source == ScheduleEntry.Source.ACADEMY:
        return True
    if viewer.is_teacher and entry.is_proposal and entry.awaits_review:
        return entry.created_by_id == viewer.pk
    return False


def can_review(entry, viewer):
    """Only management accepts or rejects a proposal, and only once."""
    return viewer.can_manage_users and entry.is_proposal and entry.awaits_review


def _time_to_pct(t):
    hours = t.hour + t.minute / 60
    return max(0.0, (hours - DAY_START_HOUR) / DAY_SPAN_HOURS * 100)


def _hour_bar_position(entry):
    """Position within the vertical day track: top = start of day, bottom = end."""
    top = _time_to_pct(entry.start_time)
    height = max(4.0, _time_to_pct(entry.end_time) - top)
    # Formatted as plain strings (not float) so Django's uk-locale template
    # rendering doesn't swap in a comma decimal separator and break the CSS.
    return f'{top:.1f}', f'{height:.1f}'


def _duration_minutes(entry):
    start = entry.start_time.hour * 60 + entry.start_time.minute
    end = entry.end_time.hour * 60 + entry.end_time.minute
    return end - start


def build_month_grid(entries, anchor: dt.date, viewer):
    """Weeks x days for the month of `anchor`, with entries annotated per-viewer."""
    by_day = defaultdict(list)
    for entry in entries:
        modifiable = can_modify(entry, viewer)
        entry.deletable = modifiable
        entry.editable = modifiable
        entry.reviewable = can_review(entry, viewer)
        entry.top_pct, entry.height_pct = _hour_bar_position(entry)
        # Shorter events sit on top of longer ones, like Google Calendar / Outlook.
        entry.z_index = max(1, 700 - _duration_minutes(entry))
        by_day[entry.date].append(entry)
    for day_entries in by_day.values():
        day_entries.sort(key=lambda e: e.start_time)

    today = dt.date.today()
    weeks = []
    for week in month_weeks(anchor):
        weeks.append([
            {
                'date': day,
                'in_month': day.month == anchor.month,
                'is_today': day == today,
                'entries': by_day.get(day, []),
            }
            for day in week
        ])
    return weeks
