from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

class Profile(models.Model):
    username = models.ForeignKey(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=100, default="hello, world!")
    profile_picture = models.ImageField(default='profiles/pfps/default.webp', upload_to='profiles/pfps/')
    date_made = models.DateTimeField(default=timezone.now)
    followers = models.ManyToManyField(User, blank=True, related_name='followers')