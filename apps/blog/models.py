
from django.db.models import (
    Model,
    CharField,
    SlugField,
    ForeignKey,
    TextField,
    TextChoices,
    DateTimeField,
    CASCADE,
    SET_NULL,
    ManyToManyField
) 
from django.utils.translation import gettext as _
from parler.models import TranslatableModel, TranslatedFields

from apps.users.models import CustomUser

class Category(TranslatableModel):
    """
    Docstring для Category
    """ 

    translations = TranslatedFields(
        name = CharField(
        max_length=100,
        unique=True,
        verbose_name=_("name")
    )
    )
    slug = SlugField(
        unique=True
    )

    class Meta:
        verbose_name = _("category")

    def __repr__(self)-> str:
        """
        Returns the official string representation of the object.
        """
        return f"Category(id = {self.id}, name={self.name})"
    
    def __str__(self)-> str:
        """
        Returns the string
        """
        return f"Name:{self.name}"


class Tag(Model):
    """
    Docstring для Tag
    """
    name = CharField(
        max_length=50
    )
    slug = SlugField(
        unique=True
    )

    def __str__(self)->str:
        return f"Name:{self.name}"
    
    def __repr__(self)->str:
        return f"Tag(id={self.id}, name={self.name})"


class Post(Model):
    """
    Docstring для Post
    """
    author = ForeignKey(
        CustomUser,
        on_delete=CASCADE,
        related_name='owner_post'
    )
    title = CharField(
        max_length=200
    )
    slug = SlugField(
        unique=True
    )
    body = TextField()
    category = ForeignKey(
        Category,
        on_delete=SET_NULL,
        blank=True,
        null=True,
        related_name='post'
    )
    tags = ManyToManyField(
        Tag,
        blank=True,
        related_name='post'
    )

    class Status(TextChoices):
        DRAFT = 'draft','Draft'
        PUBLISHED = 'published','Published'
        SCHEDULED = 'scheduled','Scheduled'

    status = CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT
    )
    created_at = DateTimeField(
        auto_now_add=True
    )
    updated_at = DateTimeField(
        auto_now=True
    )
    publish_at = DateTimeField(
        null=True,
        blank=True
    )   

    def __str__(self)-> str:
        return f"Post author: {self.author},category: {self.category}, title: {self.title}"
    

class Comment(Model):
    """
    Model Comment 
    """
    post = ForeignKey(
        Post,
        on_delete=CASCADE,
        related_name='comments'
    )
    author = ForeignKey(
        CustomUser,
        on_delete=CASCADE,
        related_name="owner"
    )
    body = TextField()
    created_at = DateTimeField(
        auto_now_add=True
    )

    def __str__(self)->str:
        return f"Post name: {self.post},author: {self.author}"

