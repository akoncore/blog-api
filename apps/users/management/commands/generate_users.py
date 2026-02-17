# apps/users/management/commands/generate_users.py

"""
Management команда для генерации тестовых пользователей.

Usage:
    python manage.py generate_users --count 100
    python manage.py generate_users --count 50 --superusers 5
    python manage.py generate_users --clear  # Удалить всех пользователей
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.cache import cache
from apps.users.models import CustomUser
from faker import Faker
import random
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Генерирует тестовых пользователей для разработки'

    def add_arguments(self, parser):
        """Добавляет аргументы командной строки."""
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Количество пользователей для создания (default: 10)'
        )
        parser.add_argument(
            '--superusers',
            type=int,
            default=0,
            help='Количество суперпользователей (default: 0)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить всех существующих пользователей перед генерацией'
        )
        parser.add_argument(
            '--locale',
            type=str,
            default='en_US',
            help='Локаль для Faker (default: en_US, можно: ru_RU, kk_KZ)'
        )

    def handle(self, *args, **options):
        """Основной метод команды."""
        count = options['count']
        superusers_count = options['superusers']
        clear = options['clear']
        locale = options['locale']

        # Валидация
        if count < 0:
            raise CommandError('Count должен быть >= 0')
        
        if superusers_count < 0:
            raise CommandError('Superusers должен быть >= 0')
        
        if superusers_count > count:
            raise CommandError('Superusers не может быть больше count')

        # Очистка существующих пользователей
        if clear:
            self._clear_users()

        # Генерация пользователей
        if count > 0:
            self._generate_users(count, superusers_count, locale)
        
        # Инвалидация кеша
        self._invalidate_cache()
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Генерация завершена!')
        )

    def _clear_users(self):
        """Удаляет всех существующих пользователей."""
        self.stdout.write('Удаление существующих пользователей...')
        
        # Сохраняем текущего пользователя (если есть)
        current_count = CustomUser.objects.count()
        
        if current_count == 0:
            self.stdout.write('  Нет пользователей для удаления')
            return
        
        # Подтверждение
        confirm = input(
            f'Вы уверены, что хотите удалить {current_count} пользователей? (yes/no): '
        )
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('  Отменено'))
            return
        
        # Удаление
        CustomUser.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Удалено {current_count} пользователей')
        )

    def _generate_users(self, count: int, superusers_count: int, locale: str):
        """
        Генерирует пользователей.
        
        Args:
            count: Общее количество пользователей
            superusers_count: Количество суперпользователей
            locale: Локаль для Faker
        """
        self.stdout.write(f'\nГенерация {count} пользователей...')
        
        fake = Faker(locale)
        
        # Списки для bulk создания
        regular_users = []
        superusers = []
        
        # Используемые email для проверки уникальности
        used_emails = set(
            CustomUser.objects.values_list('email', flat=True)
        )
        
        # Генерация обычных пользователей
        regular_count = count - superusers_count
        
        self.stdout.write(f'  Создание {regular_count} обычных пользователей...')
        
        for i in range(regular_count):
            user = self._create_user_instance(fake, used_emails, is_superuser=False)
            if user:
                regular_users.append(user)
            
            # Progress bar
            if (i + 1) % 10 == 0:
                self.stdout.write(f'    {i + 1}/{regular_count}', ending='\r')
        
        # Генерация суперпользователей
        if superusers_count > 0:
            self.stdout.write(f'\n  Создание {superusers_count} суперпользователей...')
            
            for i in range(superusers_count):
                user = self._create_user_instance(fake, used_emails, is_superuser=True)
                if user:
                    superusers.append(user)
                
                # Progress bar
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'    {i + 1}/{superusers_count}', ending='\r')
        
        # Bulk создание в БД
        self.stdout.write('\n  Сохранение в базу данных...')
        
        created_count = 0
        
        with transaction.atomic():
            if regular_users:
                CustomUser.objects.bulk_create(regular_users, batch_size=100)
                created_count += len(regular_users)
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Создано {len(regular_users)} обычных пользователей')
                )
            
            if superusers:
                CustomUser.objects.bulk_create(superusers, batch_size=100)
                created_count += len(superusers)
                self.stdout.write(
                    self.style.SUCCESS(f'    ✓ Создано {len(superusers)} суперпользователей')
                )
        
        # Статистика
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Всего создано: {created_count} пользователей'))
        self.stdout.write('='*50)
        
        # Примеры пользователей
        self._show_sample_users(regular_users[:3], superusers[:2])

    def _create_user_instance(
        self,
        fake: Faker,
        used_emails: set,
        is_superuser: bool = False
    ) -> CustomUser:
        """
        Создаёт instance пользователя (не сохраняет в БД).
        
        Args:
            fake: Faker instance
            used_emails: Множество использованных email
            is_superuser: Создать суперпользователя
        
        Returns:
            CustomUser instance или None если не удалось создать уникальный email
        """
        # Генерация уникального email
        max_attempts = 10
        email = None
        
        for _ in range(max_attempts):
            email = fake.email()
            if email not in used_emails:
                used_emails.add(email)
                break
        else:
            logger.warning(f'Не удалось создать уникальный email за {max_attempts} попыток')
            return None
        
        # Генерация данных
        full_name = fake.name()
        
        # Пароль: для тестирования используем простой
        # В продакшене это НЕДОПУСТИМО!
        password = 'password123'
        
        # Создание instance
        user = CustomUser(
            email=email,
            full_name=full_name,
            is_active=True,
            is_staff=is_superuser,
            is_superuser=is_superuser,
        )
        
        # Хешируем пароль
        user.set_password(password)
        
        return user

    def _show_sample_users(self, regular_users: list, superusers: list):
        """Показывает примеры созданных пользователей."""
        if not regular_users and not superusers:
            return
        
        self.stdout.write('\nПримеры созданных пользователей:')
        self.stdout.write('-'*50)
        
        if regular_users:
            self.stdout.write(self.style.WARNING('\nОбычные пользователи:'))
            for user in regular_users:
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Name:  {user.full_name}')
                self.stdout.write(f'  Pass:  password123')
                self.stdout.write('')
        
        if superusers:
            self.stdout.write(self.style.ERROR('\nСуперпользователи:'))
            for user in superusers:
                self.stdout.write(f'  Email: {user.email}')
                self.stdout.write(f'  Name:  {user.full_name}')
                self.stdout.write(f'  Pass:  password123')
                self.stdout.write('')
        
        self.stdout.write('-'*50)
        self.stdout.write(
            self.style.WARNING('⚠️  Все пароли: password123 (только для разработки!)')
        )

    def _invalidate_cache(self):
        """Инвалидирует кеш пользователей."""
        try:
            redis_client = cache.client.get_client()
            
            # Удаляем все ключи связанные с пользователями
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
                    self.style.SUCCESS(f'\n✓ Инвалидировано {deleted_count} ключей кеша')
                )
        
        except Exception as e:
            logger.warning(f'Не удалось инвалидировать кеш: {e}')