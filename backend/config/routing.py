from django.urls import path

from apps.collaboration.consumers import CollaborationConsumer, NotificationConsumer
from apps.notifications.consumers import UserNotificationConsumer

websocket_urlpatterns = [
    path("ws/collaborate/<uuid:document_id>/", CollaborationConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/user-notifications/", UserNotificationConsumer.as_asgi()),
]
