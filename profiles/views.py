from django.shortcuts import render, reverse, redirect
from .models import Profile
from videos.models import Video
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.views import View
from django.db.models import Q
from .forms import UserRegisterForm, ProfileUpdateForm, CreateProfileForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .decorators import user_not_authenticated
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from .tokens import account_activation_token
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.conf import settings
import os

class ProfileIndex(ListView):
    model = Profile
    template_name = "profiles/index.html"
    paginate_by = 9

    def get_queryset(self):
        sort_by = self.request.GET.get('sort-by')
        if sort_by == 'date-desc':
            queryset = Profile.objects.order_by('-date_made')
        elif sort_by == 'date-asc':
            queryset = Profile.objects.order_by('date_made')
        else:
            queryset = Profile.objects.order_by('date_made')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sort_by'] = self.request.GET.get('sort-by')
        return context

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()

        messages.success(request, "Thank you for your email confirmation. Now you can login your account.")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid!")

class CreateProfile(LoginRequiredMixin, CreateView):
    model = Profile
    fields = ['profile_picture', 'bio']
    template_name = "profiles/create_profile.html"
    def form_valid(self, form):
        if Profile.objects.filter(username=self.request.user).exists():
            raise ValidationError("you already have a profile associated with this account")
        else:
            form.instance.username = self.request.user
            return super().form_valid(form)

    def get_success_url(self):
        return reverse('detail-profile', kwargs={'pk': self.object.pk})

@user_not_authenticated
def register(req):
    if req.method == "POST":
        Form = UserRegisterForm(req.POST)
        if Form.is_valid():
            user = Form.save(commit=False)
            user.is_active=False
            user.save()
            username = Form.cleaned_data.get("username")
            activateEmail(req, user, Form.cleaned_data.get('email'))
            return redirect("login")
    else:
        Form = UserRegisterForm()
    return render(req, "profiles/register.html", {'form': Form})

def activateEmail(request, user, to_email):
    mail_subject = "Activate your user account."
    message = render_to_string("template_activate_account.html", {
        'user': user,
        'domain': "localhost:8000",
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
        "protocol": 'https' if request.is_secure() else 'http'
    })
    email = EmailMessage(mail_subject, message, to=[to_email])
    if email.send():
        messages.success(request, f"Dear {user}, please go to you email {to_email} inbox and click on \
                received activation link to confirm and complete the registration. Note: If you can't find the email, check your spam folder.")
    else:
        messages.error(request, f'Problem sending email to {to_email}, check if you typed it correctly.')

@login_required
def profile(request):
    username = request.GET.get('username', request.user)
    profile = Profile.objects.get(username=username)
    followers = profile.followers
    hi = profile.pk
    info = Profile.objects.get(pk=hi).bio
    pfp = Profile.objects.get(pk=hi).profile_picture
    username = Profile.objects.get(pk=hi).username
    poopie = Profile.objects.get(pk=hi).pk
    posts = Video.objects.all().order_by('-date_posted').filter(uploader=username)
    profile = Profile.objects.get(pk=poopie)
    followers = profile.followers.all()
    follow_num = len(followers)

    if len(followers) == 0:
        is_following = False

    for follower in followers:
        if follower == request.user:
            is_following = True
            break
        else:
            is_following = False

    context = {
        'info': info,
        'poopie': poopie,
        'pfp': pfp,
        'username': username,
        'detail_profile_list': posts,
        'follow_num': follow_num,
        'is_following': is_following,
    }
    return render(request, 'profiles/detail_profile.html', context)

@login_required
def create_profile(request):
    user = request.user
    has_profile = Profile.objects.filter(username=user).exists()
    if has_profile:
        return redirect('profile-page')
    
    if request.method == "POST":
        profile = Profile(username=user)
        form = CreateProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid() and os.path.getsize(f"./media/profiles/pfps/{profile.profile_picture.name}") < 1000000:
            form.save()
            messages.success(request, "Account Created")
            return redirect('profile-page')
        else:
            form.add_error(None, "An error occurred while making your profile. Please make sure the profile picture is under a megabyte and try again.")
    else:
        form = CreateProfileForm()
    
    context = {
        'form': form
    }
    return render(request, "profiles/create_profile.html", context)

class DetailProfileIndex(ListView):
    model = Profile
    template_name = 'profiles/detail_profile.html'
    def get(self, request, *args, **kwargs):
        hi = self.kwargs['pk']
        info = Profile.objects.get(pk=hi).bio
        pfp = Profile.objects.get(pk=hi).profile_picture
        username = Profile.objects.get(pk=hi).username
        poopie = Profile.objects.get(pk=hi).pk
        posts = Video.objects.all().order_by('-date_posted').filter(uploader=username)
        profile = Profile.objects.get(pk=poopie)
        followers = profile.followers.all()
        follow_num = len(followers)

        if len(followers) == 0:
            is_following = False

        for follower in followers:
            if follower == request.user:
                is_following = True
                break
            else:
                is_following = False

        context = {
            'info': info,
            'poopie': poopie,
            'pfp': pfp,
            'username': username,
            'detail_profile_list': posts,
            'follow_num': follow_num,
            'is_following': is_following,
        }
        return render(request, 'profiles/detail_profile.html', context)

class UpdateProfile(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    fields = ['profile_picture','bio']
    template_name = "profiles/create_profile.html"
    def form_valid(self, form):
        form.instance.username = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('detail-profile', kwargs={'pk': self.object.pk})

    def test_func(self):
        profile = self.get_object()
        return self.request.user == profile.username

class DeleteProfile(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
	model = Profile
	template_name = 'profiles/delete_profile.html'

	def get_success_url(self):
		profile = self.get_object()
		Video.objects.filter(uploader=profile.username).delete()
		return reverse('index')
	
	def test_func(self):
		profile = self.get_object()
		return self.request.user == profile.username

class AddFollower(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        hi = self.kwargs['pk']
        profilething = Profile.objects.get(pk=hi)
        if request.user != profilething.username:
            profilething.followers.add(request.user)
        
        return redirect('detail-profile', pk=profilething.pk)
         
class RemoveFollower(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        hi = self.kwargs['pk']
        profilething = Profile.objects.get(pk=hi)
        if request.user != profilething.username:
            profilething.followers.remove(request.user)
        
        return redirect('detail-profile', pk=profilething.pk)

class UserSearch(View):
	def get(self, request, *args, **kwargs):
		query = self.request.GET.get('query')
		profile_list = Profile.objects.filter(
			Q(username__username__icontains=query)
		)

		context = {
			'profile_list': profile_list
		}

		return render(request, 'profiles/search.html', context)