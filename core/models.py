from django.db import models


class ContactRequest(models.Model):
    """Заявка з публічного сайту — з Академії чи з Центру харчових інновацій.

    Одна таблиця на обидва сайти: відповідають ті самі люди, а `source` каже,
    з якої форми прийшла заявка.
    """

    class Source(models.TextChoices):
        ACADEMY = 'academy', 'Академія дистиляції'
        CENTER = 'center', 'Центр харчових інновацій'

    source = models.CharField('Звідки', max_length=20, choices=Source.choices,
                              default=Source.ACADEMY)
    name = models.CharField("Ім'я", max_length=200)
    phone = models.CharField('Телефон', max_length=50)
    email = models.EmailField('Email', blank=True)
    interest = models.CharField('Що вас цікавить', max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на консультацію'
        verbose_name_plural = 'Заявки на консультацію'

    def __str__(self):
        return f'{self.name} ({self.phone})'
