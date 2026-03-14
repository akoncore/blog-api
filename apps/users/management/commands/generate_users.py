# apps/users/management/commands/generate_users.py

"""
Management команда для генерации тестовых пользователей.

Usage:
    python manage.py generate_users --count 100
    python manage.py generate_users --count 50 --superusers 5
    python manage.py generate_users --clear
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.cache import cache
from apps.users.models import CustomUser
from faker import Faker
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Генерирует тестовых пользователей для разработки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Количество пользователей (default: 10)'
        )
        parser.add_argument(
            '--superusers',
            type=int,
            default=0,
            help='Количество суперпользователей'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить всех пользователей перед генерацией'
        )
        parser.add_argument(
            '--locale',
            type=str,
            default='en_US',
            help='Локаль Faker (en_US, ru_RU, kk_KZ)'
        )

    def handle(self, *args, **options):
        count = options['count']
        superusers_count = options['superusers']
        clear = options['clear']
        locale = options['locale']

        if count < 0:
            raise CommandError('Count должен быть >= 0')

        if superusers_count > count:
            raise CommandError('Superusers не может быть больше count')

        if clear:
            self._clear_users()

        if count > 0:
            self._generate_users(count, superusers_count, locale)

        self._invalidate_cache()

        self.stdout.write(self.style.SUCCESS('\n✓ Генерация завершена!'))

    # -------------------------------------------------------

    def _clear_users(self):
        self.stdout.write('Удаление существующих пользователей...')

        current_count = CustomUser.objects.count()

        if current_count == 0:
            self.stdout.write('Нет пользователей для удаления')
            return

        confirm = input(
            f'Удалить {current_count} пользователей? (yes/no): '
        )

        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Отменено'))
            return

        CustomUser.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(f'✓ Удалено {current_count} пользователей')
        )

    # -------------------------------------------------------

    def _generate_users(self, count: int, superusers_count: int, locale: str):

        self.stdout.write(f'\nГенерация {count} пользователей...')

        fake = Faker(locale)

        regular_users = []
        superusers = []

        used_emails = set(
            CustomUser.objects.values_list('email', flat=True)
        )

        regular_count = count - superusers_count

        self.stdout.write(f'Создание {regular_count} обычных пользователей...')

        for _ in range(regular_count):
            user = self._create_user_instance(fake, used_emails, False)
            if user:
                regular_users.append(user)

        if superusers_count > 0:
            self.stdout.write(f'Создание {superusers_count} суперпользователей...')

            for _ in range(superusers_count):
                user = self._create_user_instance(fake, used_emails, True)
                if user:
                    superusers.append(user)

        self.stdout.write('\nСохранение в базу данных...')

        created_count = 0

        with transaction.atomic():

            if regular_users:
                CustomUser.objects.bulk_create(regular_users, batch_size=100)
                created_count += len(regular_users)

            if superusers:
                CustomUser.objects.bulk_create(superusers, batch_size=100)
                created_count += len(superusers)

        self.stdout.write(
            self.style.SUCCESS(f'\nВсего создано: {created_count} пользователей')
        )

        self._show_sample_users(regular_users[:3], superusers[:2])

    # -------------------------------------------------------

    def _create_user_instance(self, fake: Faker, used_emails: set, is_superuser=False):

        max_attempts = 10
        email = None

        for _ in range(max_attempts):
            email = fake.email()
            if email not in used_emails:
                used_emails.add(email)
                break
        else:
            logger.warning('Не удалось создать уникальный email')
            return None

        first_name = fake.first_name()
        last_name = fake.last_name()

        password = 'password123'

        user = CustomUser(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_staff=is_superuser,
            is_superuser=is_superuser,
        )

        user.set_password(password)

        return user

    # -------------------------------------------------------

    def _show_sample_users(self, regular_users: list, superusers: list):

        if not regular_users and not superusers:
            return

        self.stdout.write('\nПримеры созданных пользователей:')
        self.stdout.write('-'*40)

        if regular_users:
            self.stdout.write('\nОбычные пользователи:')

            for user in regular_users:
                self.stdout.write(f'Email: {user.email}')
                self.stdout.write(f'Name: {user.first_name} {user.last_name}')
                self.stdout.write('Pass: password123\n')

        if superusers:
            self.stdout.write('\nСуперпользователи:')

            for user in superusers:
                self.stdout.write(f'Email: {user.email}')
                self.stdout.write(f'Name: {user.first_name} {user.last_name}')
                self.stdout.write('Pass: password123\n')

    # -------------------------------------------------------

    def _invalidate_cache(self):

        try:
            redis_client = cache.client.get_client()

            patterns = [
                'myapp:1:users_*',
                'myapp:1:user_*',
            ]

            deleted_count = 0

            for pattern in patterns:
                keys = redis_client.keys(pattern)

                if keys:
                    redis_client.delete(*keys)
                    deleted_count += len(keys)

            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Инвалидировано {deleted_count} ключей кеша'
                    )
                )

        except Exception as e:
            logger.warning(f'Ошибка очистки кеша: {e}')
