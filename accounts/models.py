from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    position = models.CharField(max_length=100, verbose_name='职位')
    phone_number = models.CharField(max_length=20, verbose_name='电话号码', default='')

    def __str__(self):
        return self.username
