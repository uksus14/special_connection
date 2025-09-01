from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Markdown, DowntimeChange, TextChange, TitleChange, OwnershipChange

admin.site.register(User, UserAdmin)
admin.site.register(Markdown)
admin.site.register(DowntimeChange)
admin.site.register(TextChange)
admin.site.register(TitleChange)
admin.site.register(OwnershipChange)