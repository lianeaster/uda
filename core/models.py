from django.db import models


class ContactRequest(models.Model):
    """A "Не визначились із курсом?" consultation request from the public site."""

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
