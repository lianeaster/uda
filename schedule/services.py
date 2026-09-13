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


def entry_color(entry):
    """Blue = bare course reservation. Green = course + subject + teacher all set.

    Where a blue and a green entry overlap in time, the overlapping range is
    rendered as a separate orange segment on top of both (see `overlap_segments`).
    """
    return 'green' if (entry.subject_id and entry.teacher_id) else 'blue'


def can_modify(entry, viewer):
    """Whether `viewer` may edit or delete this entry — same rule for both.

    A teacher may modify anything assigned to them (green: course + subject +
    teacher all set) regardless of who created it — a super-admin or manager
    assigning them a fully specified slot counts too. A bare Academy course
    reservation (blue) stays off-limits even if it names them as the teacher,
    and another teacher's entries are always off-limits.
    """
    if viewer.is_super_admin:
        return True
    if viewer.is_manager:
        return entry.source == ScheduleEntry.Source.ACADEMY
    if viewer.is_teacher:
        return entry.teacher_id == viewer.pk and entry_color(entry) == 'green'
    return False


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


def overlap_segments(day_entries):
    """Where a blue and a green entry overlap in time, the intersection is
    drawn as its own orange segment on top of both (Google Calendar style)."""
    segments = []
    for i, a in enumerate(day_entries):
        for b in day_entries[i + 1:]:
            if a.color == b.color or not a.overlaps(b):
                continue
            start = max(a.start_time, b.start_time)
            end = min(a.end_time, b.end_time)
            top = _time_to_pct(start)
            height = max(2.0, _time_to_pct(end) - top)
            segments.append({'top_pct': f'{top:.1f}', 'height_pct': f'{height:.1f}'})
    return segments


def build_month_grid(entries, anchor: dt.date, viewer):
    """Weeks x days for the month of `anchor`, with entries annotated per-viewer."""
    entries = list(entries)
    by_day = defaultdict(list)
    for entry in entries:
        entry.color = entry_color(entry)
        modifiable = can_modify(entry, viewer)
        entry.deletable = modifiable
        entry.editable = modifiable
        entry.top_pct, entry.height_pct = _hour_bar_position(entry)
        # Shorter events sit on top of longer ones, like Google Calendar / Outlook.
        entry.z_index = max(1, 700 - _duration_minutes(entry))
        by_day[entry.date].append(entry)
    for day_entries in by_day.values():
        day_entries.sort(key=lambda e: e.start_time)

    day_overlaps = {}
    for day, day_entries in by_day.items():
        day_overlaps[day] = overlap_segments(day_entries)
        conflicted = set()
        for i, a in enumerate(day_entries):
            for b in day_entries[i + 1:]:
                if a.color != b.color and a.overlaps(b):
                    conflicted.add(a.pk)
                    conflicted.add(b.pk)
        for entry in day_entries:
            entry.has_conflict = entry.pk in conflicted

    today = dt.date.today()
    weeks = []
    for week in month_weeks(anchor):
        weeks.append([
            {
                'date': day,
                'in_month': day.month == anchor.month,
                'is_today': day == today,
                'entries': by_day.get(day, []),
                'overlaps': day_overlaps.get(day, []),
            }
            for day in week
        ])
    return weeks
