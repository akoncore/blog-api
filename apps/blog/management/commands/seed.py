from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.utils import translation

from apps.blog.models import Category, Tag, Post, Comment

User = get_user_model()


USERS = [
    {"email": "alice@blog.com", "first_name": "Alice", "last_name": "Smith", "password": "Test1234!"},
    {"email": "bob@blog.com", "first_name": "Bob", "last_name": "Johnson", "password": "Test1234!"},
]

CATEGORIES = ["Technology", "Science", "Travel"]

TAGS = ["python", "django", "api", "tips"]

POSTS = [
    {
        "title": "DRF Guide",
        "body": "Learn DRF step by step...",
        "status": Post.Status.PUBLISHED,
        "category_name": "Technology",
        "tag_names": ["django", "api"],
        "author_index": 0,
    }
]

COMMENTS = [
    "Great post!",
    "Very useful!",
]


class Command(BaseCommand):
    help = "Seed data"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding...")

        # USERS
        users = []
        for data in USERS:
            user, _ = User.objects.get_or_create(
                email=data["email"],
                defaults=data
            )
            user.set_password(data["password"])
            user.save()
            users.append(user)

        # CATEGORY (parler FIX)
        categories = {}

        for name in CATEGORIES:
            slug = slugify(name)

            category, created = Category.objects.get_or_create(slug=slug)

            if created:
                # 🔥 маңызды
                with translation.override("en"):
                    category.name = name
                    category.save()

            categories[name] = category

        # TAGS
        tags = {}
        for name in TAGS:
            tag, _ = Tag.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name},
            )
            tags[name] = tag

        # POSTS
        posts = []
        for data in POSTS:
            post, created = Post.objects.get_or_create(
                slug=slugify(data["title"]),
                defaults={
                    "title": data["title"],
                    "body": data["body"],
                    "status": data["status"],
                    "author": users[data["author_index"]],
                    "category": categories[data["category_name"]],
                },
            )

            if created:
                post.tags.set([tags[t] for t in data["tag_names"]])

            posts.append(post)

        # COMMENTS
        for i, post in enumerate(posts):
            for j in range(2):
                Comment.objects.get_or_create(
                    post=post,
                    author=users[j % len(users)],
                    body=COMMENTS[(i + j) % len(COMMENTS)],
                )

        self.stdout.write(self.style.SUCCESS("DONE"))