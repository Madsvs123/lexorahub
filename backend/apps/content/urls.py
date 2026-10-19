from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.content.views import (
    BlockDefinitionViewSet,
    CollectionViewSet,
    ContentEntryViewSet,
    ContentTypeViewSet,
    FieldDefinitionViewSet,
    LandingPageViewSet,
    NavigationMenuViewSet,
    SeriesViewSet,
    TaxonomyViewSet,
    TermViewSet,
    TopicViewSet,
)

router = DefaultRouter()
router.register("types", ContentTypeViewSet, basename="content-type")
router.register("fields", FieldDefinitionViewSet, basename="field")
router.register("blocks", BlockDefinitionViewSet, basename="block")
router.register("taxonomies", TaxonomyViewSet, basename="taxonomy")
router.register("terms", TermViewSet, basename="term")
router.register("entries", ContentEntryViewSet, basename="entry")
router.register("series", SeriesViewSet, basename="series")
router.register("collections", CollectionViewSet, basename="collection")
router.register("topics", TopicViewSet, basename="topic")
router.register("menus", NavigationMenuViewSet, basename="menu")
router.register("landings", LandingPageViewSet, basename="landing-page")

urlpatterns = [path("", include(router.urls))]
