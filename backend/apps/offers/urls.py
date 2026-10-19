"""Offers URL routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OfferApprovalChainViewSet,
    OfferTemplateViewSet,
    OfferViewSet,
    OnboardingHandoffViewSet,
)

router = DefaultRouter()
router.register(r"offer-templates", OfferTemplateViewSet, basename="offer-templates")
router.register(
    r"offer-approval-chains", OfferApprovalChainViewSet, basename="offer-approval-chains"
)
router.register(r"offers", OfferViewSet, basename="offers")
router.register(r"onboarding-handoffs", OnboardingHandoffViewSet, basename="onboarding-handoffs")

urlpatterns = [path("", include(router.urls))]
