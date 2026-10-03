from datetime import timedelta

from django.db import migrations


def copy_old_transactions(apps, schema_editor):
    Cycle = apps.get_model('finance', 'Cycle')
    Entry = apps.get_model('finance', 'Entry')
    Income = apps.get_model('finance', 'Income')
    Expense = apps.get_model('finance', 'Expense')
    Special = apps.get_model('finance', 'Special')

    # Cycles used to be a fixed 30 days long.
    for cycle in Cycle.objects.filter(end__isnull=True):
        cycle.end = cycle.start + timedelta(days=29)
        cycle.save(update_fields=['end'])

    entries = []
    for income in Income.objects.all():
        entries.append(Entry(
            cycle_id=income.cycle_id,
            kind='income',
            title=income.source,
            amount=income.amount or 0,
            certainty=income.status,
            is_debt=income.owe_me,
            comment=income.comment,
        ))
    for expense in Expense.objects.all():
        entries.append(Entry(
            cycle_id=expense.cycle_id,
            kind='expense',
            title=expense.purpose,
            amount=expense.amount or 0,
            certainty='certain',
            is_debt=expense.i_owe,
            comment=expense.comment,
        ))
    for special in Special.objects.all():
        entries.append(Entry(
            cycle_id=special.cycle_id,
            kind=special.type,
            title=special.title,
            amount=special.amount or 0,
            certainty='uncertain',
            is_debt=special.owe_me if special.type == 'income' else special.i_owe,
            comment=special.comment,
        ))
    Entry.objects.bulk_create(entries)


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_new_money_model'),
    ]

    operations = [
        migrations.RunPython(copy_old_transactions, migrations.RunPython.noop),
    ]
