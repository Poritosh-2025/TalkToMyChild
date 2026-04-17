from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.contrib.auth.hashers import make_password, is_password_usable
from .models import (
    Child,
    ChildProfile,
    ChildSubject,
    ChildTrait,
    ChildInterest,
    ChildDislike,
)
from .utils import get_child_cache_key


# Cache invalidation for attributes
@receiver(post_save, sender=ChildSubject)
@receiver(post_save, sender=ChildTrait)
@receiver(post_save, sender=ChildInterest)
@receiver(post_save, sender=ChildDislike)
@receiver(post_delete, sender=ChildSubject)
@receiver(post_delete, sender=ChildTrait)
@receiver(post_delete, sender=ChildInterest)
@receiver(post_delete, sender=ChildDislike)
def invalidate_child_cache_on_attribute_change(sender, instance, **kwargs):
    """Invalidate intelligence cache when any attribute changes."""
    cache.delete(get_child_cache_key(instance.child_id, "intelligence"))


# Auto-hash ChildProfile password if set directly (e.g., via admin or ORM)
@receiver(pre_save, sender=ChildProfile)
def hash_child_password(sender, instance, **kwargs):
    """Hash the password if it's not already hashed."""
    if instance.password and not is_password_usable(instance.password):
        instance.password = make_password(instance.password)
