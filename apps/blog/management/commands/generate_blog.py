from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.contrib.auth import get_user_model

from blog.models import Category, Tag, Post, Comment  # adjust app label if needed

User = get_user_model()

# ── Seed data ─────────────────────────────────────────────────────────────────

USERS = [
    {"email": "alice@blog.com",   "full_name": "Alice Smith",   "password": "Test1234!"},
    {"email": "bob@blog.com",     "full_name": "Bob Johnson",   "password": "Test1234!"},
    {"email": "charlie@blog.com", "full_name": "Charlie Brown", "password": "Test1234!"},
    {"email": "dana@blog.com",    "full_name": "Dana White",    "password": "Test1234!"},
]

CATEGORIES = [
    "Technology",
    "Science",
    "Culture",
    "Travel",
    "Food",
]

TAGS = [
    "python",
    "django",
    "api",
    "tutorial",
    "news",
    "tips",
    "review",
    "guide",
]

POSTS = [
    {
        "title":         "Getting Started with Django REST Framework",
        "body":          (
            "Django REST Framework (DRF) is a powerful toolkit for building Web APIs. "
            "It provides serializers, viewsets, routers and authentication out of the box. "
            "In this post we walk through setting up your first API endpoint step by step. "
            "By the end you will have a fully working CRUD API with token authentication."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Technology",
        "tag_names":     ["django", "api", "tutorial"],
        "author_index":  0,
    },
    {
        "title":         "Python Tips and Tricks for Clean Code",
        "body":          (
            "Writing clean Python code means following PEP 8, using meaningful names, "
            "keeping functions small and leveraging list comprehensions wisely. "
            "Here are ten habits that will make your codebase easier to read and maintain. "
            "We also cover type hints, dataclasses and the walrus operator."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Technology",
        "tag_names":     ["python", "tips"],
        "author_index":  1,
    },
    {
        "title":         "A Beginner's Guide to REST APIs",
        "body":          (
            "REST stands for Representational State Transfer. "
            "APIs built on REST principles use HTTP verbs — GET, POST, PATCH, DELETE — "
            "to perform CRUD operations on resources identified by URLs. "
            "Status codes, headers and JSON payloads are the building blocks of every REST API."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Technology",
        "tag_names":     ["api", "guide"],
        "author_index":  2,
    },
    {
        "title":         "Exploring the Science of Sleep",
        "body":          (
            "Sleep is not a passive state. During deep sleep the brain consolidates memories, "
            "flushes out toxins and repairs tissue. "
            "Adults need 7–9 hours per night for optimal cognitive performance and physical health. "
            "We explore the four stages of sleep and what happens when you skip them."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Science",
        "tag_names":     ["news", "review"],
        "author_index":  3,
    },
    {
        "title":         "Street Food Culture Around the World",
        "body":          (
            "From Bangkok's pad thai vendors to Istanbul's simit carts, street food is the "
            "most honest expression of a city's culinary identity. "
            "It is cheap, fast, delicious and deeply tied to local tradition. "
            "Join us on a tour of the world's best street food scenes."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Food",
        "tag_names":     ["review", "tips"],
        "author_index":  0,
    },
    {
        "title":         "Hiking the Tian Shan Mountains",
        "body":          (
            "The Tian Shan range stretches across Kazakhstan, Kyrgyzstan and China. "
            "Its peaks exceed 7 000 metres and its valleys hide pristine alpine lakes. "
            "We cover three multi-day routes accessible from Almaty, including gear lists "
            "and the best seasons to attempt each trail."
        ),
        "status":        Post.Status.PUBLISHED,
        "category_name": "Travel",
        "tag_names":     ["guide", "tips"],
        "author_index":  1,
    },
    {
        "title":         "Draft: Advanced Django ORM Techniques",
        "body":          (
            "This draft covers select_related, prefetch_related, annotate, aggregate "
            "and raw SQL escape hatches. "
            "Work in progress — examples and benchmarks to be added."
        ),
        "status":        Post.Status.DRAFT,
        "category_name": "Technology",
        "tag_names":     ["django", "python"],
        "author_index":  0,
    },
    {
        "title":         "Draft: The Future of Quantum Computing",
        "body":          (
            "Quantum computers exploit superposition and entanglement to solve problems "
            "that are intractable for classical machines. "
            "Draft — literature review in progress."
        ),
        "status":        Post.Status.DRAFT,
        "category_name": "Science",
        "tag_names":     ["news"],
        "author_index":  2,
    },
]

COMMENTS = [
    "Great post, really helpful — thanks!",
    "This is exactly what I was looking for.",
    "Could you write a follow-up on this topic?",
    "Very well explained, I bookmarked this.",
    "I learned a lot from this article.",
    "Excellent write-up, keep it up!",
]


class Command(BaseCommand):
    help = "Seed the database with test users, categories, tags, posts and comments."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("\n  Seeding blog data...\n"))

        # ── Guard: skip if already seeded ──────────────────────────────────────
        if User.objects.filter(email="alice@blog.com").exists():
            self.stdout.write(
                self.style.WARNING("  ⚠  Test data already exists — skipping.\n")
            )
            return

        # ── 1. Users ───────────────────────────────────────────────────────────
        users = []
        for data in USERS:
            user = User.objects.create_user(
                email=data["email"],
                full_name=data["full_name"],
                password=data["password"],
            )
            users.append(user)
            self.stdout.write(
                self.style.SUCCESS(f"  ✔  User      : {user.email}")
            )

        # ── 2. Categories ──────────────────────────────────────────────────────
        categories = {}
        for name in CATEGORIES:
            category, _ = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name},
            )
            categories[name] = category
        self.stdout.write(
            self.style.SUCCESS(f"  ✔  Categories: {len(categories)} created")
        )

        # ── 3. Tags ────────────────────────────────────────────────────────────
        tags = {}
        for name in TAGS:
            tag, _ = Tag.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name},
            )
            tags[name] = tag
        self.stdout.write(
            self.style.SUCCESS(f"  ✔  Tags      : {len(tags)} created")
        )

        # ── 4. Posts ───────────────────────────────────────────────────────────
        posts = []
        for data in POSTS:
            post, created = Post.objects.get_or_create(
                slug=slugify(data["title"]),
                defaults={
                    "title":    data["title"],
                    "body":     data["body"],
                    "status":   data["status"],
                    "author":   users[data["author_index"]],
                    "category": categories[data["category_name"]],
                },
            )
            if created:
                post.tags.set(
                    [tags[t] for t in data["tag_names"] if t in tags]
                )
            posts.append(post)
        self.stdout.write(
            self.style.SUCCESS(f"  ✔  Posts     : {len(posts)} created")
        )

        # ── 5. Comments ────────────────────────────────────────────────────────
        comment_count = 0
        published_posts = [p for p in posts if p.status == Post.Status.PUBLISHED]
        for i, post in enumerate(published_posts):
            for j in range(3):
                Comment.objects.get_or_create(
                    post=post,
                    author=users[j % len(users)],
                    body=COMMENTS[(i + j) % len(COMMENTS)],
                )
                comment_count += 1
        self.stdout.write(
            self.style.SUCCESS(f"  ✔  Comments  : {comment_count} created")
        )

        # ── Summary ────────────────────────────────────────────────────────────
        published = sum(1 for p in posts if p.status == Post.Status.PUBLISHED)
        drafts    = sum(1 for p in posts if p.status == Post.Status.DRAFT)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("  ✔  Seed complete!\n"))
        self.stdout.write(f"  Users      : {len(users)}  (password: Test1234!)")
        for u in users:
            self.stdout.write(f"               {u.email}")
        self.stdout.write(f"  Categories : {len(categories)}")
        self.stdout.write(f"  Tags       : {len(tags)}")
        self.stdout.write(f"  Posts      : {len(posts)}  ({published} published, {drafts} drafts)")
        self.stdout.write(f"  Comments   : {comment_count}")
        self.stdout.write("")