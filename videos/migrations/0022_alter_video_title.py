# Generated by Django 4.1.3 on 2022-11-13 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0021_remove_comment_parent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='video',
            name='title',
            field=models.TextField(max_length=50),
        ),
    ]
