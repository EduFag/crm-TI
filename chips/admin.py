from django.contrib import admin

from chips.models import Batch, Chip, ChipMovement, Operator, Recharge


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'received_at')
    search_fields = ('nome',)
    date_hierarchy = 'received_at'


@admin.register(Chip)
class ChipAdmin(admin.ModelAdmin):
    list_display = (
        'line_number', 'operator', 'status', 'technology', 'plan_type',
        'batch', 'is_active', 'created_at',
    )
    list_filter = ('status', 'technology', 'plan_type', 'operator', 'is_active')
    search_fields = ('line_number', 'iccid')
    readonly_fields = ('created_at', 'updated_at', 'last_blocked_at')
    autocomplete_fields = ('operator', 'batch')
    date_hierarchy = 'created_at'


@admin.register(ChipMovement)
class ChipMovementAdmin(admin.ModelAdmin):
    list_display = ('chip', 'action', 'employee_name', 'employee_user', 'registered_by', 'timestamp')
    list_filter = ('action',)
    search_fields = ('employee_name', 'chip__line_number')
    readonly_fields = ('timestamp',)
    autocomplete_fields = ('chip', 'employee_user', 'registered_by')
    date_hierarchy = 'timestamp'


@admin.register(Recharge)
class RechargeAdmin(admin.ModelAdmin):
    list_display = ('chip', 'amount', 'registered_by', 'timestamp')
    search_fields = ('chip__line_number',)
    readonly_fields = ('timestamp',)
    autocomplete_fields = ('chip', 'registered_by')
    date_hierarchy = 'timestamp'
