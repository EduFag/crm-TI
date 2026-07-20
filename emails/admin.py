from django.contrib import admin

from emails.models import EmailAccount, EmailDomain


@admin.register(EmailDomain)
class EmailDomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ('get_endereco', 'employee_name', 'status', 'created_at')
    list_filter = ('status', 'domain')
    search_fields = ('username', 'employee_name', 'domain__name')
    readonly_fields = ('created_at', 'updated_at', 'get_endereco')
    autocomplete_fields = ('domain',)

    @admin.display(description='E-mail')
    def get_endereco(self, obj):
        return obj.address
