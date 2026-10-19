from rest_framework.pagination import CursorPagination, PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class CursorStandardPagination(CursorPagination):
    page_size = 25
    ordering = "created_at"
    page_size_query_param = "page_size"
