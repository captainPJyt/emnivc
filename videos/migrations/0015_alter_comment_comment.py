# Generated by Django 4.1.3 on 2022-11-11 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videos', '0014_alter_comment_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='comment',
            field=models.TextField(),
        ),
    ]
