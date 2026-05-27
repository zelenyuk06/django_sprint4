from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import CommentForm, PostForm, UserUpdateForm
from .models import Category, Comment, Post

User = get_user_model()
PAGINATE_BY = 10


def _published_posts():
    return (
        Post.objects.select_related("author", "category", "location")
        .filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )


def _paginate(request, queryset):
    return Paginator(queryset, PAGINATE_BY).get_page(request.GET.get("page"))


def index(request):
    return render(
        request,
        "blog/index.html",
        {"page_obj": _paginate(request, _published_posts())},
    )


def post_detail(request, id):
    post = get_object_or_404(Post, pk=id)
    if post.author != request.user:
        if (
            not post.is_published
            or post.pub_date > timezone.now()
            or not post.category.is_published
        ):
            raise Http404
    return render(
        request,
        "blog/detail.html",
        {
            "post": post,
            "form": CommentForm(),
            "comments": post.comments.select_related("author"),
        },
    )


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True
    )
    posts = _published_posts().filter(category=category)
    return render(
        request,
        "blog/category.html",
        {"category": category, "page_obj": _paginate(request, posts)},
    )


def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = (
        Post.objects.select_related("author", "category", "location")
        .filter(author=profile_user)
        .annotate(comment_count=Count("comments"))
        .order_by("-pub_date")
    )
    if request.user != profile_user:
        posts = posts.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        )
    return render(
        request,
        "blog/profile.html",
        {"profile": profile_user, "page_obj": _paginate(request, posts)},
    )


@login_required
def edit_profile(request):
    form = UserUpdateForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect("blog:profile", username=request.user.username)
    return render(request, "blog/user.html", {"form": form})


@login_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("blog:profile", username=request.user.username)
    return render(request, "blog/create.html", {"form": form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect("blog:post_detail", id=post_id)
    form = PostForm(
        request.POST or None, request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect("blog:post_detail", id=post_id)
    return render(request, "blog/create.html", {"form": form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect("blog:post_detail", id=post_id)
    form = PostForm(instance=post)
    if request.method == "POST":
        post.delete()
        return redirect("blog:profile", username=request.user.username)
    return render(request, "blog/create.html", {"form": form})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect("blog:post_detail", id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect("blog:post_detail", id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect("blog:post_detail", id=post_id)
    return render(
        request, "blog/comment.html", {"form": form, "comment": comment}
    )


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)
    if comment.author != request.user:
        return redirect("blog:post_detail", id=post_id)
    if request.method == "POST":
        comment.delete()
        return redirect("blog:post_detail", id=post_id)
    return render(request, "blog/comment.html", {"comment": comment})
