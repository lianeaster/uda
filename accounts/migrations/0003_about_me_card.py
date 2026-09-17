# Картка «Про мене»: фото й текстові розділи на самому користувачі.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_roles'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='about',
            field=models.TextField(blank=True, verbose_name='Про мене'),
        ),
        migrations.AddField(
            model_name='user',
            name='education',
            field=models.TextField(blank=True, verbose_name='Освіта'),
        ),
        migrations.AddField(
            model_name='user',
            name='experience',
            field=models.TextField(blank=True, verbose_name='Робочий досвід'),
        ),
        migrations.AddField(
            model_name='user',
            name='interests',
            field=models.TextField(blank=True, verbose_name='Інтереси'),
        ),
        migrations.AddField(
            model_name='user',
            name='patronymic',
            field=models.CharField(blank=True, max_length=150, verbose_name='По батькові'),
        ),
        migrations.AddField(
            model_name='user',
            name='photo',
            field=models.ImageField(blank=True, upload_to='profiles/', verbose_name='Фото'),
        ),
    ]
