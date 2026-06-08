from django.contrib import admin

from helpdesk.models import Comment, Ticket, TicketCategory


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'priority', 'requester_name', 'created_at')
    list_filter = ('status', 'priority', 'category', 'is_archived')
    search_fields = ('title', 'requester_name')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'created_at', 'is_active')
    list_filter = ('is_active',)
