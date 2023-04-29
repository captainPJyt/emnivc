from django.contrib import admin
from django.urls import path
from .views import ProfileIndex, DetailProfileIndex, UpdateProfile, DeleteProfile, AddFollower, RemoveFollower, UserSearch, create_profile

urlpatterns = [
    path('', ProfileIndex.as_view(), name='profile-index'),
    path('create', create_profile, name='create_profile'),
    path('<int:pk>/', DetailProfileIndex.as_view(), name='detail-profile'),
    path('<int:pk>/update', UpdateProfile.as_view(), name='profile-update'),
    path('<int:pk>/delete', DeleteProfile.as_view(), name='profile-delete'),
    path('<int:pk>/followers/add', AddFollower.as_view(), name='add-follower'),
    path('<int:pk>/followers/remove', RemoveFollower.as_view(), name='remove-follower'),
    path('search/', UserSearch.as_view(), name='profile-search'),
]