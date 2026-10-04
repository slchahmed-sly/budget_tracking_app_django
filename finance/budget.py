"""
Budget calculations for a cycle.

The plan is the cycle's *certain* entries: certain income minus certain
expenses (rent, bills, debts, savings transfers) is the cycle's free money,
spread over the days left. Probable/uncertain entries are only added in
the "potential" number.
"""
from dataclasses import dataclass, field

from django.utils import timezone

from .models import Entry

RING_CIRCUMFERENCE = 276.46  # 2 * pi * 44, the radius used by the days ring


@dataclass
class CycleSummary:
    total_days: int
    days_left: int
    income: int
    expenses: int
    free_money: int
    per_day: int
    pending_net: int
    potential_per_day: int
    ring_dash: float
    certain_entries: list = field(default_factory=list)
    pending_entries: list = field(default_factory=list)


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

    return CycleSummary(
        total_days=total_days,
        days_left=days_left,
        income=income,
        expenses=expenses,
        free_money=free_money,
        per_day=round(free_money / days_left),
        pending_net=pending_net,
        potential_per_day=round((free_money + pending_net) / days_left),
        ring_dash=round(RING_CIRCUMFERENCE * days_left / total_days, 1),
        certain_entries=sorted(certain, key=lambda e: (not e.is_income, -e.amount)),
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
