from django.db.models import Case, F, IntegerField, Q, When
from rest_framework.filters import OrderingFilter, SearchFilter


class TaskSearchFilter(SearchFilter):
    """A purely numeric search term also matches the task ID."""

    def filter_queryset(self, request, queryset, view):
        term = (request.query_params.get(self.search_param) or '').strip()
        if term.isdigit():
            return queryset.filter(
                Q(pk=int(term)) | Q(title__icontains=term) | Q(description__icontains=term)
            )
        return super().filter_queryset(request, queryset, view)


class TaskOrderingFilter(OrderingFilter):
    """
    Sorts by meaning rather than by the raw column:
    priority orders Low < Medium < High < Critical, and tasks without a due date go last.
    """
    PRIORITY_RANK = Case(
        When(priority='LOW', then=1), When(priority='MEDIUM', then=2),
        When(priority='HIGH', then=3), When(priority='CRITICAL', then=4),
        output_field=IntegerField(),
    )

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset
        terms = []
        for term in ordering:
            descending = term.startswith('-')
            field = term.lstrip('-')
            if field == 'priority':
                queryset = queryset.annotate(priority_rank=self.PRIORITY_RANK)
                terms.append(('-' if descending else '') + 'priority_rank')
            elif field == 'due_date':
                expr = F('due_date')
                terms.append(expr.desc(nulls_last=True) if descending else expr.asc(nulls_last=True))
            else:
                terms.append(term)
        return queryset.order_by(*terms, '-id')
