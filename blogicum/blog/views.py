from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, get_user_model
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, ProfileEditForm, PostForm, CommentForm
from django.utils import timezone
from .models import Post, Category, Comment
from django.db.models import Count


User = get_user_model()


def get_published_posts():
    return Post.objects.filter(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    ).annotate(
        comment_count=Count('comments'),
    ).select_related(
        'author', 'location', 'category'
    ).order_by('-pub_date')


def post_list(request):
    post_list = get_published_posts()

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'page_obj': page_obj}

    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        post = get_object_or_404(
            get_published_posts(),
            pk=post_id,
        )

    comments = post.comments.all()
    form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'form': form,
    }

    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True,
    )

    post_list = get_published_posts().filter(
        category=category,
    )

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj,
    }

    return render(request, 'blog/category.html', context)


def registration(request):
    form = RegistrationForm(request.POST or None)

    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('blog:index')

    return render(
        request,
        'registration/registration_form.html',
        {'form': form},
    )
    

def profile(request, username):
    profile = get_object_or_404(User, username=username)

    if request.user == profile:
        post_list = Post.objects.filter(author=profile)
    else:
        post_list = get_published_posts().filter(author=profile)

    post_list = post_list.annotate(
        comment_count=Count('comments'),
    ).select_related(
        'author', 'location', 'category'
    ).order_by('-pub_date')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': profile,
        'page_obj': page_obj,
    }

    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    form = ProfileEditForm(
        request.POST or None,
        instance=request.user,
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:profile',
            username=request.user.username,
        )

    return render(
        request,
        'blog/user.html',
        {'form': form},
    )
    
@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(
            'blog:profile',
            username=request.user.username,
        )

    return render(
        request,
        'blog/create.html',
        {'form': form},
    )


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    return render(
        request,
        'blog/create.html',
        {'form': form},
    )
    
    
@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    if request.method == 'POST':
        post.delete()
        return redirect(
            'blog:profile',
            username=request.user.username,
        )

    return render(
        request,
        'blog/create.html',
        {'form': PostForm(instance=post)},
    )
    

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    is_published = (
        post.is_published
        and post.pub_date <= timezone.now()
        and post.category.is_published
    )

    if not is_published and request.user != post.author:
        return get_object_or_404(
            get_published_posts(),
            pk=post_id,
        )

    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect(
        'blog:post_detail',
        post_id=post_id,
    )
    
    
@login_required
def edit_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post=post,
    )

    if request.user != comment.author:
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    form = CommentForm(
        request.POST or None,
        instance=comment,
    )

    if form.is_valid():
        form.save()
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    return render(
        request,
        'blog/comment.html',
        {
            'form': form,
            'comment': comment,
            'post': post,
        },
    )
    

@login_required
def delete_comment(request, post_id, comment_id):
    post = get_object_or_404(Post, pk=post_id)
    comment = get_object_or_404(
        Comment,
        pk=comment_id,
        post=post,
    )

    if request.user != comment.author:
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    if request.method == 'POST':
        comment.delete()
        return redirect(
            'blog:post_detail',
            post_id=post_id,
        )

    return render(
        request,
        'blog/comment.html',
        {
            'comment': comment,
            'post': post,
        },
    )
    