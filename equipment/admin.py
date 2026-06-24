from django.contrib import admin

from equipment.models import Equipment, EquipmentLog


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'tag', 'brand_model', 'type', 'status', 'current_employee',
        'warranty_end', 'get_garantia_expirada', 'created_at',
    )
    list_filter = ('type', 'status')
    search_fields = ('tag', 'serial_number', 'brand_model', 'current_employee')
    readonly_fields = ('created_at', 'updated_at', 'get_garantia_expirada')
    date_hierarchy = 'created_at'

    @admin.display(description='Garantia expirada', boolean=True)
    def get_garantia_expirada(self, obj):
        return obj.is_warranty_expired


@admin.register(EquipmentLog)
class EquipmentLogAdmin(admin.ModelAdmin):
    """Histórico de movimentações — somente leitura no admin."""

    list_display = ('equipment', 'action', 'employee_name', 'timestamp')
    list_filter = ('action',)
    search_fields = ('equipment__tag', 'employee_name')
    readonly_fields = ('equipment', 'action', 'employee_name', 'timestamp')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
