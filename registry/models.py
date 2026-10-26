from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils import timezone

from registry.services.rules import RECORD_TYPES


class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        LIVE = "live", "Live"
        REMOVED = "removed", "Removed"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submissions",
    )
    subdomain = models.CharField(max_length=63)
    legal_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    portfolio_url = models.URLField(max_length=500)
    github_username = models.CharField(max_length=39, blank=True)
    record_type = models.CharField(
        max_length=5,
        choices=[(record_type, record_type) for record_type in RECORD_TYPES],
        default="CNAME",
    )
    record_value = models.CharField(max_length=512)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    dns_cleaned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                Lower("subdomain"),
                condition=Q(status__in=["pending", "live"]),
                name="unique_active_subdomain",
            )
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="submission_status_created_idx"),
            models.Index(fields=["email"], name="submission_email_idx"),
            models.Index(fields=["ip", "created_at"], name="submission_ip_created_idx"),
            models.Index(fields=["user", "status"], name="submission_user_status_idx"),
        ]

    def __str__(self):
        return f"{self.subdomain}.{settings.ZONE} ({self.status})"

    @property
    def url(self) -> str:
        return f"https://{self.subdomain}.{settings.ZONE}"

    @property
    def is_live(self) -> bool:
        return self.status == self.Status.LIVE

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    def get_absolute_url(self) -> str:
        return reverse("submit_done", args=[self.pk])

    def is_owned_by(self, user) -> bool:
        return bool(user and user.is_authenticated and self.user_id == user.pk)
