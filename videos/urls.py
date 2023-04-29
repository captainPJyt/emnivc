from django.contrib import admin
from django.urls import path
from .views import CreateVideo, DetailVideo, UpdateVideo, DeleteVideo, AddLike, Dislike, DownloadVideo, VideoSearch, update_video_view_count

urlpatterns = [
    path('create/', CreateVideo.as_view(), name='video-create'),
    path('<int:pk>/', DetailVideo.as_view(), name='video-detail'),
    path('<int:pk>/update', UpdateVideo.as_view(), name='video-update'),
    path('<int:pk>/delete', DeleteVideo.as_view(), name='video-delete'),
    path('<int:pk>/like', AddLike.as_view(), name='video-like'),
    path('<int:pk>/dislike', Dislike.as_view(), name='video-dislike'),
    path('<int:pk>/download', DownloadVideo.as_view(), name='video-download'),
    path('update_elapsed_time/<int:pk>', update_video_view_count),
    path('search/', VideoSearch.as_view(), name='video-search'),
]