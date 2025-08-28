from django.contrib import admin
from .models import Theme, SourceChannel, TargetChannel

@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "code")

@admin.register(SourceChannel)
class SourceChannelAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "theme")

@admin.register(TargetChannel)
class TargetChannelAdmin(admin.ModelAdmin):
    list_display = ("tg_id", "name", "theme")