from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from chips.models import Chip, Operator, Batch

# ----------------- OPERATOR (RF06) -----------------
class OperatorListView(LoginRequiredMixin, ListView):
    model = Operator
    template_name = 'chips/operator_list.html'
    context_object_name = 'operators'

class OperatorCreateView(LoginRequiredMixin, CreateView):
    model = Operator
    fields = ['name', 'status']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:operator_list')

# ----------------- BATCH (RF06) -----------------
class BatchListView(LoginRequiredMixin, ListView):
    model = Batch
    template_name = 'chips/batch_list.html'
    context_object_name = 'batches'

class BatchCreateView(LoginRequiredMixin, CreateView):
    model = Batch
    fields = ['identifier', 'status']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:batch_list')

# ----------------- CHIP (RF05, RF07) -----------------
class ChipListView(LoginRequiredMixin, ListView):
    model = Chip
    template_name = 'chips/chip_list.html'
    context_object_name = 'chips'
    
    def get_queryset(self):
        return Chip.objects.select_related('operator', 'batch').all().order_by('-created_at')

class ChipCreateView(LoginRequiredMixin, CreateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:chip_list')

class ChipUpdateView(LoginRequiredMixin, UpdateView):
    model = Chip
    fields = ['line_number', 'status', 'technology', 'fixed_cost', 'iccid', 'plan_type', 'operator', 'batch']
    template_name = 'chips/form_base.html'
    success_url = reverse_lazy('chips:chip_list')
