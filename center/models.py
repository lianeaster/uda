from django.db import models
from django.urls import reverse
from django.utils import timezone


class News(models.Model):
    """Матеріал розділу «Новини та події».

    Розділ має бути живим, тож матеріали пишуть в адмінці, а не в коді.
    Рубрик кілька, і порожні на сайті не показуються: сторінка виводить лише
    опубліковані матеріали, а рубрика — це підпис на картці, не фільтр.
    """

    class Rubric(models.TextChoices):
        CENTER = 'center', 'Новини Центру'
        TECH = 'tech', 'Технології та переробка'
        PRODUCTS = 'products', 'Розробка продуктів'
        EVENTS = 'events', 'Навчання та події'
        PARTNERS = 'partners', 'Проєкти й партнерства'
        BUSINESS = 'business', 'Можливості для бізнесу'

    title = models.CharField('Заголовок', max_length=200)
    slug = models.SlugField('Адреса', max_length=120, unique=True,
                            help_text='Латиницею, через дефіс: /news/<адреса>/')
    rubric = models.CharField('Рубрика', max_length=20, choices=Rubric.choices,
                              default=Rubric.CENTER)
    date = models.DateField('Дата', default=timezone.localdate)
    summary = models.CharField('Коротко', max_length=300,
                               help_text='Одне-два речення для картки в списку.')
    body = models.TextField('Текст', help_text='Абзаци — через порожній рядок.')
    is_published = models.BooleanField('Опубліковано', default=False)

    class Meta:
        ordering = ['-date', '-pk']
        verbose_name = 'Новина'
        verbose_name_plural = 'Новини та події'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('center:news_detail', args=[self.slug])
