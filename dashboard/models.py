from django.db import models
from django.contrib.auth import get_user_model
from apps.tours.models import Tour

User = get_user_model()


class TourPhoto(models.Model):
    """
    A photo uploaded by a guide for a specific tour.

    Photos are stored under MEDIA_ROOT/tour_photos/YYYY/MM/ and served
    via MEDIA_URL. Each photo is linked to the tour and the guide who uploaded it.

    Ordering is newest-first so the most recent photos appear at the top of the gallery.

    ASSUMPTIONS:
    - Pillow is installed (required for ImageField and image validation)
    - MEDIA_ROOT and MEDIA_URL are configured in settings
    - Photo files are cleaned up manually on delete (the view handles file deletion)
    """

    tour = models.ForeignKey(
        Tour,
        on_delete=models.CASCADE,  # photos are deleted when the tour is deleted
        related_name='photos',
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,  # keep photo even if guide account is deleted
        null=True,
        related_name='uploaded_photos',
    )
    photo = models.ImageField(
        upload_to='tour_photos/%Y/%m/',  # organised by year/month for easy management
    )
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Metadata: newest photos first, human-readable names."""

        ordering = ['-uploaded_at']  # newest first in gallery view
        verbose_name = 'Tour Photo'
        verbose_name_plural = 'Tour Photos'

    def __str__(self):
        """Return a human-readable label for admin/shell use."""
        return f'Photo for {self.tour} ({self.uploaded_at.date() if self.uploaded_at else "unsaved"})'
