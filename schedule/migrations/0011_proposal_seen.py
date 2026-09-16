from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('schedule', '0010_schedule_on_groups')]

    operations = [
        migrations.AddField(
            model_name='scheduleentry',
            name='author_seen_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='Порожньо — рішення ще не показане тому, хто пропонував.',
                verbose_name='Автор побачив рішення'),
        ),
    ]
