from django.contrib import admin
from .models import Team, Match, Player, Goal, Group, Document

admin.site.register(Team)
admin.site.register(Match)
admin.site.register(Player)
admin.site.register(Goal)
admin.site.register(Group)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file')