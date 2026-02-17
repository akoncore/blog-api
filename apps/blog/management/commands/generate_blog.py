# apps/blog/management/commands/generate_blog.py

"""
Management команда для генерации тестовых данных блога.

Usage:
    python manage.py generate_blog --posts 100 --comments 500
    python manage.py generate_blog --categories 10 --tags 20
    python manage.py generate_blog --full  # Полная генерация
    python manage.py generate_blog --clear  # Очистка данных
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.cache import cache
from django.utils.text import slugify
from django.db.models import Count

# ИСПРАВЛЕННЫЕ ИМПОРТЫ - используйте свои пути к моделям
try:
    from apps.blog.models import Category, Tag, Post, Comment
    from apps.users.models import CustomUser
except ImportError:
    # Альтернативные пути импорта
    try:
        from blog.models import Category, Tag, Post, Comment
        from users.models import CustomUser
    except ImportError:
        raise ImportError(
            "Не удалось импортировать модели. Проверьте структуру проекта."
        )

from faker import Faker
import random
import logging
from typing import List

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Генерирует тестовые данные для блога'

    def add_arguments(self, parser):
        """Добавляет аргументы командной строки."""
        parser.add_argument(
            '--categories',
            type=int,
            default=0,
            help='Количество категорий (default: 0)'
        )
        parser.add_argument(
            '--tags',
            type=int,
            default=0,
            help='Количество тегов (default: 0)'
        )
        parser.add_argument(
            '--posts',
            type=int,
            default=0,
            help='Количество постов (default: 0)'
        )
        parser.add_argument(
            '--comments',
            type=int,
            default=0,
            help='Количество комментариев (default: 0)'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Полная генерация (категории: 10, теги: 30, посты: 100, комментарии: 500)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить все данные блога перед генерацией'
        )
        parser.add_argument(
            '--locale',
            type=str,
            default='en_US',
            help='Локаль для Faker (en_US, ru_RU, kk_KZ)'
        )
        parser.add_argument(
            '--publish-events',
            action='store_true',
            help='Публиковать события в Redis Pub/Sub при создании комментариев'
        )

    def handle(self, *args, **options):
        """Основной метод команды."""
        # Обработка full флага
        if options['full']:
            options['categories'] = 10
            options['tags'] = 30
            options['posts'] = 100
            options['comments'] = 500

        # Валидация
        self._validate_options(options)

        # Очистка данных
        if options['clear']:
            self._clear_data()

        # Проверка наличия пользователей
        if not CustomUser.objects.exists():
            raise CommandError(
                'Нет пользователей! Сначала создайте пользователей:\n'
                'python manage.py generate_users --count 10'
            )

        # Инициализация Faker
        fake = Faker(options['locale'])
        self.fake = fake

        # Генерация данных
        self.stdout.write(self.style.SUCCESS('\n🚀 Начало генерации данных блога...\n'))

        categories = []
        tags = []
        posts = []
        comments = []

        # Категории
        if options['categories'] > 0:
            categories = self._generate_categories(options['categories'])

        # Теги
        if options['tags'] > 0:
            tags = self._generate_tags(options['tags'])

        # Посты
        if options['posts'] > 0:
            posts = self._generate_posts(options['posts'], categories, tags)

        # Комментарии
        if options['comments'] > 0:
            comments = self._generate_comments(
                options['comments'],
                posts,
                options['publish_events']
            )

        # Инвалидация кеша
        self._invalidate_cache()

        # Финальная статистика
        self._show_statistics()

        self.stdout.write(
            self.style.SUCCESS('\n✓ Генерация завершена!')
        )

    def _validate_options(self, options):
        """Валидирует опции."""
        counts = [
            options['categories'],
            options['tags'],
            options['posts'],
            options['comments']
        ]

        if all(c == 0 for c in counts) and not options['clear']:
            raise CommandError(
                'Укажите хотя бы один параметр для генерации или используйте --full'
            )

        for count in counts:
            if count < 0:
                raise CommandError('Количество не может быть отрицательным')

    def _clear_data(self):
        """Очищает все данные блога."""
        self.stdout.write('Очистка данных блога...')

        counts = {
            'Комментарии': Comment.objects.count(),
            'Посты': Post.objects.count(),
            'Теги': Tag.objects.count(),
            'Категории': Category.objects.count(),
        }

        total = sum(counts.values())

        if total == 0:
            self.stdout.write('  Нет данных для удаления')
            return

        # Показываем что будет удалено
        self.stdout.write('\nБудет удалено:')
        for name, count in counts.items():
            if count > 0:
                self.stdout.write(f'  - {name}: {count}')

        # Подтверждение
        confirm = input(f'\nПродолжить? (yes/no): ')

        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('  Отменено'))
            return

        # Удаление
        with transaction.atomic():
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Удалено {total} записей')
        )

    def _generate_categories(self, count: int) -> List[Category]:
        """Генерирует категории."""
        self.stdout.write(f'Генерация {count} категорий...')

        # Предопределённые категории для блога
        category_names = [
            'Technology', 'Programming', 'Web Development', 'Mobile Apps',
            'Data Science', 'Machine Learning', 'DevOps', 'Cloud Computing',
            'Cybersecurity', 'Blockchain', 'Gaming', 'Design',
            'Business', 'Startups', 'Marketing', 'Finance',
            'Health', 'Fitness', 'Travel', 'Food',
            'Lifestyle', 'Education', 'Science', 'News',
            'Entertainment', 'Sports', 'Music', 'Art',
            'Photography', 'Books'
        ]

        # Перемешиваем и берём нужное количество
        random.shuffle(category_names)
        selected_names = category_names[:count]

        # Проверяем существующие
        existing_slugs = set(
            Category.objects.values_list('slug', flat=True)
        )

        categories = []

        for name in selected_names:
            slug = slugify(name)

            # Обеспечиваем уникальность slug
            original_slug = slug
            counter = 1
            while slug in existing_slugs:
                slug = f"{original_slug}-{counter}"
                counter += 1

            existing_slugs.add(slug)

            category = Category(
                name=name,
                slug=slug
            )
            categories.append(category)

        # Bulk создание
        with transaction.atomic():
            Category.objects.bulk_create(categories, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Создано {len(categories)} категорий')
        )

        return list(Category.objects.all())

    def _generate_tags(self, count: int) -> List[Tag]:
        """Генерирует теги."""
        self.stdout.write(f'Генерация {count} тегов...')

        # Предопределённые теги
        tag_names = [
            'python', 'javascript', 'react', 'django', 'vue',
            'nodejs', 'typescript', 'angular', 'flutter', 'swift',
            'kotlin', 'java', 'csharp', 'php', 'ruby',
            'go', 'rust', 'scala', 'elixir', 'haskell',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'mongodb', 'postgresql', 'mysql', 'redis', 'elasticsearch',
            'api', 'rest', 'graphql', 'microservices', 'serverless',
            'ai', 'ml', 'deep-learning', 'nlp', 'computer-vision',
            'frontend', 'backend', 'fullstack', 'mobile', 'web',
            'tutorial', 'guide', 'tips', 'best-practices', 'beginner',
            'advanced', 'intermediate', 'performance', 'security', 'testing'
        ]

        random.shuffle(tag_names)
        selected_names = tag_names[:count]

        existing_slugs = set(
            Tag.objects.values_list('slug', flat=True)
        )

        tags = []

        for name in selected_names:
            slug = slugify(name)

            # Уникальность
            original_slug = slug
            counter = 1
            while slug in existing_slugs:
                slug = f"{original_slug}-{counter}"
                counter += 1

            existing_slugs.add(slug)

            tag = Tag(
                name=name,
                slug=slug
            )
            tags.append(tag)

        # Bulk создание
        with transaction.atomic():
            Tag.objects.bulk_create(tags, ignore_conflicts=True)

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Создано {len(tags)} тегов')
        )

        return list(Tag.objects.all())

    def _generate_posts(
        self,
        count: int,
        categories: List[Category],
        tags: List[Tag]
    ) -> List[Post]:
        """Генерирует посты."""
        self.stdout.write(f'Генерация {count} постов...')

        # Получаем всех пользователей
        users = list(CustomUser.objects.all())

        if not users:
            raise CommandError('Нет пользователей для создания постов')

        # Если нет категорий/тегов, создаём базовые
        if not categories:
            categories = self._generate_categories(5)

        if not tags:
            tags = self._generate_tags(10)

        existing_slugs = set(
            Post.objects.values_list('slug', flat=True)
        )

        posts = []

        for i in range(count):
            # Генерация данных
            title = self.fake.sentence(nb_words=6).rstrip('.')
            slug = slugify(title)

            # Уникальность slug
            original_slug = slug
            counter = 1
            while slug in existing_slugs:
                slug = f"{original_slug}-{counter}"
                counter += 1

            existing_slugs.add(slug)

            # Тело поста (несколько параграфов)
            body = '\n\n'.join([
                self.fake.paragraph(nb_sentences=random.randint(5, 10))
                for _ in range(random.randint(3, 8))
            ])

            # Случайный автор
            author = random.choice(users)

            # Случайная категория
            category = random.choice(categories) if random.random() > 0.1 else None

            # Статус (80% published, 20% draft)
            status = Post.Status.PUBLISHED if random.random() > 0.2 else Post.Status.DRAFT

            post = Post(
                author=author,
                title=title,
                slug=slug,
                body=body,
                category=category,
                status=status
            )
            posts.append(post)

            # Progress
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  {i + 1}/{count}', ending='\r')

        # Bulk создание
        with transaction.atomic():
            Post.objects.bulk_create(posts, batch_size=100)

            # Добавление тегов (M2M нельзя в bulk_create)
            self.stdout.write('\n  Добавление тегов к постам...')

            for post in Post.objects.filter(
                slug__in=[p.slug for p in posts]
            ):
                # Случайное количество тегов (0-5)
                num_tags = random.randint(0, min(5, len(tags)))
                if num_tags > 0:
                    selected_tags = random.sample(tags, num_tags)
                    post.tags.set(selected_tags)

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Создано {len(posts)} постов')
        )

        return list(Post.objects.all())

    def _generate_comments(
        self,
        count: int,
        posts: List[Post],
        publish_events: bool = False
    ) -> List[Comment]:
        """Генерирует комментарии."""
        self.stdout.write(f'Генерация {count} комментариев...')

        # Получаем опубликованные посты
        if not posts:
            posts = list(Post.objects.filter(status=Post.Status.PUBLISHED))

        if not posts:
            self.stdout.write(
                self.style.WARNING('  ⚠️  Нет опубликованных постов для комментариев')
            )
            return []

        users = list(CustomUser.objects.all())

        if not users:
            raise CommandError('Нет пользователей для создания комментариев')

        comments = []

        for i in range(count):
            # Случайный пост
            post = random.choice(posts)

            # Случайный автор
            author = random.choice(users)

            # Тело комментария
            body = self.fake.paragraph(nb_sentences=random.randint(1, 5))

            comment = Comment(
                post=post,
                author=author,
                body=body
            )
            comments.append(comment)

            # Progress
            if (i + 1) % 10 == 0:
                self.stdout.write(f'  {i + 1}/{count}', ending='\r')

        # Bulk создание
        with transaction.atomic():
            Comment.objects.bulk_create(comments, batch_size=100)

        self.stdout.write(
            self.style.SUCCESS(f'\n  ✓ Создано {len(comments)} комментариев')
        )

        # Публикация событий в Redis Pub/Sub (опционально)
        if publish_events:
            self._publish_comment_events(comments)

        return comments

    def _publish_comment_events(self, comments: List[Comment]):
        """Публикует события о создании комментариев в Redis Pub/Sub."""
        self.stdout.write('  Публикация событий в Redis Pub/Sub...')

        published = 0

        for comment in comments:
            try:
                # ИСПРАВЛЕНО: используем прямой доступ к Redis
                redis_client = cache.client.get_client()
                
                import json
                import time
                
                event = {
                    'event': 'comment_created',
                    'timestamp': time.time(),
                    'data': {
                        'id': comment.id,
                        'post_id': comment.post.id,
                        'post_title': comment.post.title,
                        'author_id': comment.author.id,
                        'author_name': comment.author.full_name,
                        'body': comment.body[:100],
                        'created_at': comment.created_at.isoformat(),
                    }
                }
                
                message = json.dumps(event, ensure_ascii=False)
                redis_client.publish('comments', message)
                
                published += 1

            except Exception as e:
                logger.error(f'Failed to publish event for comment {comment.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Опубликовано {published} событий')
        )

    def _invalidate_cache(self):
        """Инвалидирует кеш блога."""
        try:
            redis_client = cache.client.get_client()

            patterns = [
                'myapp:1:posts_*',
                'myapp:1:post_*',
                'myapp:1:comments_*',
                'myapp:1:categories_*',
                'myapp:1:tags_*',
            ]

            deleted_count = 0
            for pattern in patterns:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
                    deleted_count += len(keys)

            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'\n✓ Инвалидировано {deleted_count} ключей кеша')
                )

        except Exception as e:
            logger.warning(f'Не удалось инвалидировать кеш: {e}')

    def _show_statistics(self):
        """Показывает статистику созданных данных."""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('СТАТИСТИКА БЛОГА'))
        self.stdout.write('='*60)

        stats = {
            'Категории': Category.objects.count(),
            'Теги': Tag.objects.count(),
            'Посты (всего)': Post.objects.count(),
            'Посты (опубликовано)': Post.objects.filter(status=Post.Status.PUBLISHED).count(),
            'Посты (черновики)': Post.objects.filter(status=Post.Status.DRAFT).count(),
            'Комментарии': Comment.objects.count(),
            'Пользователи': CustomUser.objects.count(),
        }

        for name, count in stats.items():
            self.stdout.write(f'{name:.<40} {count:>5}')

        self.stdout.write('='*60)

        # Дополнительная статистика
        if Post.objects.exists():
            avg_comments = Comment.objects.count() / Post.objects.count()
            self.stdout.write(f'\nСреднее комментариев на пост: {avg_comments:.1f}')

            most_commented_post = Post.objects.annotate(
                comment_count=Count('comments')
            ).order_by('-comment_count').first()

            if most_commented_post:
                comment_count = most_commented_post.comment_count
                self.stdout.write(
                    f'Больше всего комментариев: "{most_commented_post.title}" '
                    f'({comment_count})'
                )