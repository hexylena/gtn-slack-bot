# Generated by Django 4.0.3 on 2022-07-08 09:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0006_alter_certificaterequest_approved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='certificaterequest',
            name='approved',
            field=models.CharField(choices=[('ACC', 'Accepted'), ('REJ', 'Rejected'), ('UNK', 'Unknown'), ('S/S', 'Certificate Sent'), ('R/S', 'Rejection Sent')], default='UNK', max_length=3),
        ),
    ]
