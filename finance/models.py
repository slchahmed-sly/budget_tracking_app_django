from django.db import models
from django.core.exceptions import ValidationError


STATUS_CHOICES = [
    ('certain', 'Certain (Green)'),
    ('probable', 'Probable (Yellow)'),
    ('uncertain', 'Uncertain (Red)'),
]


class Cycle(models.Model):
    start  = models.DateField()
    title = models.CharField(max_length=100)
    mru_to_tl = models.DecimalField(max_digits=6,decimal_places=2)

    def __str__(self):
        return f'{self.title}'

class RecurringExpense(models.Model):
    amount_mru = models.PositiveIntegerField()
    amount_tl = models.PositiveIntegerField()
    title = models.CharField(max_length = 100)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.title}: {self.amount_tl}'

class BaseTransaction(models.Model):
    """
    This model will not create a database table. 
    It is just a template for other models.
    """
    amount_mru = models.PositiveIntegerField(blank=True, null=True)
    amount_tl = models.PositiveIntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)
    
    # We define the Foreign Key here because every transaction needs a cycle.
    # TIP: We use '%(class)s' in related_name to automatically generate 
    # unique names like 'incomes', 'expenses', 'specials'.
    cycle = models.ForeignKey(
        Cycle, 
        on_delete=models.CASCADE, 
        related_name='%(class)s' 
    )

    class Meta:
        abstract = True  # This is the magic line

    def clean(self):
        if not self.amount_mru and not self.amount_tl:
            raise ValidationError("You must provide either MRU or TL amount.")

    def save(self, *args, **kwargs):
       
        if self.pk:
          
            old_record = self.__class__.objects.get(pk=self.pk)
            
            if self.amount_tl != old_record.amount_tl:
                
                self.amount_mru = int(round(self.amount_tl * self.cycle.mru_to_tl))
            
            elif self.amount_mru != old_record.amount_mru:
                
                self.amount_tl = int(round(self.amount_mru / self.cycle.mru_to_tl))
            
        else:
            
            if self.amount_mru and not self.amount_tl:
                self.amount_tl = int(round(self.amount_mru / self.cycle.mru_to_tl))
            elif self.amount_tl:
                self.amount_mru = int(round(self.amount_tl * self.cycle.mru_to_tl))
        
        super().save(*args, **kwargs)






class Expense(BaseTransaction):
    purpose = models.CharField(max_length=100)
    i_owe = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.purpose}: {self.amount_tl}'


class Income(BaseTransaction):
    source = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='certain')
    owe_me = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.source}: {self.amount_tl}'


class Special(BaseTransaction):
    purpose = models.CharField(max_length=100)
    i_owe = models.BooleanField(default=False)
    owe_me = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.purpose}: {self.amount_tl}'

