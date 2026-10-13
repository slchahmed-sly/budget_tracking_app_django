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


MAX_PROGRESS_DOTS = 10


@dataclass
class Side:
    """The certain entries going one way (in or out), split by whether
    they have been received/paid yet. Ticking only changes this split,
    never the free money."""
    total: int
    open: list
    done: list

    @property
    def open_total(self):
        return sum(e.amount for e in self.open)

    @property
    def done_total(self):
        return sum(e.amount for e in self.done)

    @property
    def count(self):
        return len(self.open) + len(self.done)

    @property
    def dots(self):
        """One dot per item, ticked ones first; empty when there are too many to draw."""
        if self.count > MAX_PROGRESS_DOTS:
            return []
        return [True] * len(self.done) + [False] * len(self.open)


@dataclass
class CycleSummary:
    total_days: int
    days_left: int
    day_number: int
    income: int
    expenses: int
    free_money: int
    per_day: int
    pending_net: int
    potential_per_day: int
    planned_percent: int
    ring_dash: float
    incoming: Side
    outgoing: Side
    certain_entries: list = field(default_factory=list)
    pending_entries: list = field(default_factory=list)


def _side(entries):
    by_size = sorted(entries, key=lambda e: -e.amount)
    return Side(
        total=sum(e.amount for e in entries),
        open=[e for e in by_size if not e.is_done],
        done=[e for e in by_size if e.is_done],
    )


def summarize(cycle, today=None):
    today = today or timezone.localdate()
    entries = list(cycle.entries.all())
    total_days = cycle.total_days
    days_left = min(max((cycle.end - today).days + 1, 1), total_days)

    certain = [e for e in entries if e.is_certain]
    pending = [e for e in entries if not e.is_certain]

    incoming = _side([e for e in certain if e.is_income])
    outgoing = _side([e for e in certain if not e.is_income])
    free_money = incoming.total - outgoing.total
    pending_net = sum(e.signed_amount for e in pending)

    return CycleSummary(
        total_days=total_days,
        days_left=days_left,
        day_number=total_days - days_left + 1,
        income=incoming.total,
        expenses=outgoing.total,
        free_money=free_money,
        per_day=round(free_money / days_left),
        pending_net=pending_net,
        potential_per_day=round((free_money + pending_net) / days_left),
        planned_percent=round(outgoing.total * 100 / incoming.total) if incoming.total else 0,
        ring_dash=round(RING_CIRCUMFERENCE * days_left / total_days, 1),
        incoming=incoming,
        outgoing=outgoing,
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
