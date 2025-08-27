from django.db import models

class Theme(models.Model):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.code

class Channel(models.Model):
    tgstat_id = models.BigIntegerField(unique=True, db_index=True)
    tg_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    link = models.URLField(max_length=500, blank=True, null=True)
    peer_type = models.CharField(max_length=50, default="channel")
    title = models.CharField(max_length=500, blank=True, null=True)
    about = models.TextField(blank=True, null=True)
    image100 = models.URLField(max_length=500, blank=True, null=True)
    image640 = models.URLField(max_length=500, blank=True, null=True)
    participants_count = models.BigIntegerField(default=0)
    ci_index = models.FloatField(default=0.0)
    tgstat_restrictions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(blank=True, null=True)
    stored_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "channel"
        indexes = [
            models.Index(fields=["participants_count"]),
            models.Index(fields=["ci_index"]),
        ]

    def __str__(self):
        return f"{self.username or self.title} ({self.participants_count})"
