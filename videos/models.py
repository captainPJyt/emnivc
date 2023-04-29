from django.db import models
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User
from profiles.models import Profile

class Video(models.Model, object):
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    description = models.TextField(max_length=75)
    video_file = models.FileField(upload_to='uploads/video_files/', validators=[FileExtensionValidator(allowed_extensions=['mp4', 'mov'])])
    thumbnail = models.ImageField(upload_to='uploads/thumbnails/')
    date_posted = models.DateTimeField(default=timezone.now)
    likes = models.ManyToManyField(User, blank=True, related_name='video_likes')
    dislikes = models.ManyToManyField(User, blank=True, related_name='video_dislikes')
    views = models.ManyToManyField(User, blank=True, related_name='video_views')
    duration = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
	comment = models.TextField(max_length=150)
	date_posted = models.DateTimeField(default=timezone.now)
	commenter = models.ForeignKey(User, on_delete=models.CASCADE)
	post = models.ForeignKey('Video', on_delete=models.CASCADE)
	likes = models.ManyToManyField(User, blank=True, related_name='comment_likes')
	dislikes = models.ManyToManyField(User, blank=True, related_name='comment_dislikes')

	class Meta:
		ordering = ['-date_posted']