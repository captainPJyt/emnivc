from django.shortcuts import render, reverse, redirect
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from .models import Video, Comment
from django.db.models import Q
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing import CompositeVideoClip
from moviepy.video.VideoClip import TextClip
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from profiles.models import Profile
from .forms import CommentForm
from django.http import HttpResponseRedirect, FileResponse
from django.views import View
import os
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import datetime, timedelta
from django.http import JsonResponse
import time
from .tasks import update_video_view_count
from django.views.decorators.http import require_POST
from urllib.parse import urlencode

@require_POST
def update_elapsed_time(request, video_id):
    key = f"user:{request.user.pk}:video:{video_id}"
    start_time = cache.get(key)
    if start_time is None:
        start_time = time.time()
        cache.set(key, start_time, timeout=None)
    elapsed_time = float(request.POST.get('elapsed_time', 0))
    cache.set(f"{key}:elapsed_time", elapsed_time, timeout=None)
    return JsonResponse({'status': 'ok'})

class Index(ListView):
    model = Video
    template_name = 'videos/index.html'
    context_object_name = 'videos'
    paginate_by = 9

    def get_queryset(self):
        sort_by = self.request.GET.get('sort-by')
        if sort_by == 'date-desc':
            queryset = Video.objects.order_by('-date_posted')
        elif sort_by == 'date-asc':
            queryset = Video.objects.order_by('date_posted')
        elif sort_by == 'views-desc':
            queryset = Video.objects.order_by('-views')
        elif sort_by == 'likes-desc':
            queryset = Video.objects.order_by('-likes')
        else:
            queryset = Video.objects.order_by('-views')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        uploader_profiles = {}
        for video in context['videos']:
            uploader = video.uploader
            if uploader not in uploader_profiles:
                uploader_profiles[uploader] = Profile.objects.get(username__username=uploader)
        context['uploader_profiles'] = uploader_profiles
        context['sort_by'] = self.request.GET.get('sort-by')
        return context

class CreateVideo(LoginRequiredMixin, CreateView):
    model = Video
    fields = ['title', 'description', 'video_file', 'thumbnail']
    template_name = 'videos/create_video.html'

    def form_valid(self, form):
        cooldown_valid = True
        last_upload_time = cache.get(f"last_upload_{self.request.user.id}")

        if last_upload_time is not None and datetime.now() < last_upload_time + timedelta(minutes=0):
            form.add_error(None, "You can only upload one video every 2 minutes.")
            cooldown_valid = False
            return super().form_invalid(form)

        if cooldown_valid:
            cache.set(f"last_upload_{self.request.user.id}", datetime.now(), timeout=None)

        form.instance.uploader = self.request.user
        super().form_valid(form)

        video_check = self.request.FILES['video_file']
        thumbnail_check = self.request.FILES['thumbnail']
        video_check.name = video_check.name.replace(" ", "_")

        print(os.path.getsize(f"./media/uploads/thumbnails/{thumbnail_check.name}"))
    
        if os.path.exists(f"./media/uploads/video_files/{video_check.name}") and os.path.getsize(f"./media/uploads/video_files/{video_check.name}") < 1000000 and os.path.getsize(f"./media/uploads/thumbnails/{thumbnail_check.name}") < 1000000:
            try:
                vid = VideoFileClip(f"./media/uploads/video_files/{video_check.name}")
                if Profile.objects.filter(username=form.instance.uploader).exists():
                    if vid.duration <= 1.5 and vid.duration > 0:
                        self.object.duration = vid.duration
                        return super().form_valid(form)
                    else:
                        form.instance.delete()
                        form.add_error(None, "This video is longer than 1.5 seconds.")
                        return super().form_invalid(form)
                else:
                    form.instance.delete()
                    form.add_error(None, "You don't have a profile associated with this account yet. Please go to eniv.online/profiles/create to make one.")
                    return super().form_invalid(form)
            except Exception as e:
                os.remove(f"./media/uploads/video_files/{video_check.name}")
                form.instance.delete()
                form.add_error(None, "An error occurred while processing your video. Please try again.")
                return super().form_invalid(form)
        else:
            form.instance.delete()
            form.add_error(None, "An error occurred while uploading your video. Please make sure the video and thumbnail are under a megabyte and try again.")
            return super().form_invalid(form)

    def form_invalid(self, form):
        video_check = self.request.FILES['video_file']
        os.remove(f"./media/uploads/video_files/{video_check.name}")
        form.instance.delete()
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('video-detail', kwargs={'pk': self.object.pk})

class DetailVideo(DetailView):
    def get(self, request, *args, **kwargs):
        e = self.kwargs['pk']
        form = CommentForm()
        pen = Video.objects.get(pk=e)
        hi = Video.objects.get(pk=e).uploader
        thing = Profile.objects.get(username=hi).pk

        comments = Comment.objects.filter(post=pen).order_by('-date_posted')
        comment_count = comments.count()

        context = {
            'e': e,
            'thing': thing,
            'post': pen,
            'form': form,
            'comments': comments,
            'comment_amount': comment_count,
        }
        if request.user.is_authenticated:
            update_video_view_count(request.user.pk, pen.pk)

            key = f"user:{request.user.pk}:video:{pen.pk}"
            elapsed_time = cache.get(f"{key}:elapsed_time", 0)
            if elapsed_time >= 0.7 * pen.duration:
                if not cache.get(f"{key}:viewed"):
                    pen.views.add(request.user)
                    pen.save()
                    cache.set(f"{key}:viewed", 1, timeout=None)

        return render(request, 'videos/detail_video.html', context)

    def post(self, request, *args, **kwargs):
        e = self.kwargs['pk']
        pen = Video.objects.get(pk=e)
        hi = Video.objects.get(pk=e).uploader
        thing = Profile.objects.get(username=hi).pk
        form = CommentForm(request.POST)

        if form.is_valid():
            new_comment = form.save(commit=False)
            new_comment.commenter = Profile.objects.get(username=request.user).username
            new_comment.post = pen
            new_comment.save()
            return HttpResponseRedirect(f'/videos/{e}')

        comments = Comment.objects.filter(post=pen).order_by('-date_posted')

        context = {
            'e': e,
            'thing': thing,
            'post': pen,
            'form': form,
            'comments': comments,
        }
        return render(request, 'videos/detail_video.html', context)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if self.request.user.is_authenticated:
            e = self.kwargs['pk']
            pen = Video.objects.get(pk=e)
            key = f"user:{self.request.user.pk}:video:{pen.pk}"
            start_time = cache.get(key)
            if start_time is not None:
                elapsed_time = time.time() - start_time
                if elapsed_time >= 0.7 * pen.duration:
                    if not cache.get(f"{key}:viewed"):
                        pen.views.add(request.user)
                        pen.save()
                        cache.set(f"{key}:viewed", 1, timeout=None)
                        response['X-Increment-View-Count'] = True
            cache.set(key, time.time(), timeout=None)

        return response

class UpdateVideo(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Video
    fields = ['title', 'description']
    template_name = 'videos/create_video.html'

    def get_success_url(self):
        return reverse('video-detail', kwargs={'pk': self.object.pk})

    def test_func(self):
        video = self.get_object()
        return self.request.user == video.uploader

class DeleteVideo(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Video
    template_name = 'videos/delete_video.html'

    def get_success_url(self):
        return reverse('index')
    
    def test_func(self):
        video = self.get_object()
        return self.request.user == video.uploader
    
def add_view(request, video):
    print("Ayc")

    if request.user in video.views.all():
        video.views.add(request.user)

class AddLike(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        hi = self.kwargs['pk']
        video = Video.objects.get(pk=hi)
        is_dislike = False
        for dislike in video.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break
        if is_dislike:
            video.dislikes.remove(request.user)
        is_like = False
        for like in video.likes.all():
            if like == request.user:
                is_like = True
                break
        if not is_like:
            video.likes.add(request.user)
        if is_like:
            video.likes.remove(request.user)
        scroll = self.request.POST.get('scroll')
        return redirect(f'{reverse("video-detail", kwargs={"pk": hi})}?scroll={scroll}')
        
class Dislike(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        hi = self.kwargs['pk']
        video = Video.objects.get(pk=hi)
        is_like = False
        for like in video.likes.all():
            if like == request.user:
                is_like = True
                break
        if is_like:
            video.likes.remove(request.user)
        is_dislike = False
        for dislike in video.dislikes.all():
            if dislike == request.user:
                is_dislike = True
                break
        if not is_dislike:
            video.dislikes.add(request.user)
        if is_dislike:
            video.dislikes.remove(request.user)
        scroll = self.request.POST.get('scroll')
        return redirect(f'{reverse("video-detail", kwargs={"pk": hi})}?scroll={scroll}')

class DownloadVideo(View):
    def get(self, request, *args, **kwargs):
        e = self.kwargs['pk']
        video = Video.objects.get(pk=e).video_file
        vid = Video.objects.get(pk=e)
        video_file = open(f"media/{video}", 'rb')
        response = FileResponse(video_file)
        print(video.name.removeprefix("uploads/video_files/"))

        response['Content-Type'] = 'video/mp4'
        response['Content-Disposition'] = 'attachment; filename="%s"' % vid.title.replace(" ", "_")

        return response

class VideoSearch(View):
    def get(self, request, *args, **kwargs):
        query = self.request.GET.get('query')
        video_list = Video.objects.filter(
            Q(title__icontains=query)
        )

        context = {
            'video_list': video_list
        }

        return render(request, 'videos/search.html', context)