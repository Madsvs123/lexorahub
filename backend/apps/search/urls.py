from django.urls import path

from apps.search.views import DeliverySearchView, EditorialSearchView, RelatedContentView

urlpatterns = [
    path("editorial/", EditorialSearchView.as_view(), name="editorial-search"),
    path("delivery/", DeliverySearchView.as_view(), name="delivery-search"),
    path("related/<uuid:entry_id>/", RelatedContentView.as_view(), name="related-content"),
]
