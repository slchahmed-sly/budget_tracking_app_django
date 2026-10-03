"""
Budget calculations for a cycle.

The plan is the cycle's *certain* entries: certain income minus certain
expenses (rent, bills, debts, savings transfers) is the cycle's free money.
Probable/uncertain entries are only added in the "potential" numbers.

How much free money is left depends on the latest balance check-in:
- with a check-in: balance + certain income not yet in that balance
  - certain expenses not yet paid out of that balance;
- without one: we assume the daily allowance was spent every day so far.
"""
from dataclasses import dataclass, field

from django.utils import timezone

from .models import Entry

RING_CIRCUMFERENCE = 276.46  # 2 * pi * 44, the radius used by the days ring

ON_TRACK = 'on_track'
A_BIT_FAST = 'a_bit_fast'
TOO_FAST = 'too_fast'


@dataclass
class CycleSummary:
    total_days: int
    days_left: int
    income: int
    expenses: int
    free_money: int
    free_left: int
    per_day: int
    pending_net: int
    potential_per_day: int
    pace: str
    left_percent: int
    expected_percent: int
    ring_dash: float
    checkin: object = None
    certain_entries: list = field(default_factory=list)
    pending_entries: list = field(default_factory=list)


def is_reflected(entry, checkin):
    """True when the entry's money had already moved before the check-in."""
    return entry.is_done and entry.done_at is not None and entry.done_at <= checkin.created_at


def unsettled_total(entries, checkin=None):
    """Signed total of certain entries whose money has not moved yet
    (relative to the given check-in, or to now when there is none)."""
    total = 0
    for entry in entries:
        if not entry.is_certain:
            continue
        settled = is_reflected(entry, checkin) if checkin else entry.is_done
        if not settled:
            total += entry.signed_amount
    return total


def summarize(cycle, today=None):
    today = today or timezone.localdate()
    entries = list(cycle.entries.all())
    total_days = cycle.total_days
    days_left = min(max((cycle.end - today).days + 1, 1), total_days)

    certain = [e for e in entries if e.is_certain]
    pending = [e for e in entries if not e.is_certain]

    income = sum(e.amount for e in certain if e.is_income)
    expenses = sum(e.amount for e in certain if not e.is_income)
    free_money = income - expenses
    pending_net = sum(e.signed_amount for e in pending)

    checkin = cycle.checkins.first()
    if checkin:
        free_left = checkin.balance + unsettled_total(certain, checkin)
    else:
        free_left = round(free_money * days_left / total_days)

    per_day = round(free_left / days_left)
    potential_per_day = round((free_left + pending_net) / days_left)

    expected_ratio = days_left / total_days
    left_ratio = free_left / free_money if free_money > 0 else 0
    if free_money <= 0 or left_ratio < expected_ratio - 0.15:
        pace = TOO_FAST
    elif left_ratio < expected_ratio - 0.05:
        pace = A_BIT_FAST
    else:
        pace = ON_TRACK

    income_first = sorted(certain, key=lambda e: (not e.is_income, -e.amount))
    return CycleSummary(
        total_days=total_days,
        days_left=days_left,
        income=income,
        expenses=expenses,
        free_money=free_money,
        free_left=free_left,
        per_day=per_day,
        pending_net=pending_net,
        potential_per_day=potential_per_day,
        pace=pace,
        left_percent=max(0, min(100, round(left_ratio * 100))),
        expected_percent=round(expected_ratio * 100),
        ring_dash=round(RING_CIRCUMFERENCE * expected_ratio, 1),
        checkin=checkin,
        certain_entries=income_first,
        pending_entries=sorted(pending, key=lambda e: (not e.is_income, -e.amount)),
    )


def ledger_text(entries, currency):
    lines = []
    for entry in entries:
        kind = 'Income' if entry.kind == Entry.INCOME else 'Expense'
        flags = [entry.certainty]
        if entry.is_done:
            flags.append('received' if entry.is_income else 'paid')
        if entry.is_debt:
            flags.append('owed to me' if entry.is_income else 'I owe')
        if entry.goal_id:
            flags.append(f'savings goal: {entry.goal.name}')
        note = f" [Note: {entry.comment}]" if entry.comment else ""
        lines.append(f"{kind}: {entry.title}, {entry.amount} {currency} ({', '.join(flags)}){note}")
    return "\n".join(lines)
