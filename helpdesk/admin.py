from django.contrib import admin

from helpdesk.models import (
    Comment,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketSpecificCategory,
)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ('created_at',)
    autocomplete_fields = ('author',)


class TicketAttachmentInline(admin.TabularInline):
    model = TicketAttachment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(TicketCategory)
class TicketCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(TicketSpecificCategory)
class TicketSpecificCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'category', 'specific_category', 'status', 'priority',
        'requester_name', 'assigned_to', 'is_archived', 'created_at',
    )
    list_filter = ('status', 'priority', 'category', 'is_archived', 'is_active', 'is_rejected')
    search_fields = ('title', 'requester_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('category', 'specific_category', 'equipe', 'requester_user', 'created_by', 'assigned_to')
    inlines = (CommentInline, TicketAttachmentInline)
    date_hierarchy = 'created_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('text', 'ticket__title', 'author__username')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('ticket', 'author')


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'file_name', 'created_at')
    search_fields = ('file_name', 'ticket__title')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('ticket',)
