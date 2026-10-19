"""Real-time collaborative editing via Django Channels."""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone


class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    """
    Presence, editing awareness, and operational updates for a content document.
    Protocol messages:
      {type: join|leave|presence|cursor|selection|patch|comment|note|lock|unlock}
    """

    async def connect(self):
        self.document_id = str(self.scope["url_route"]["kwargs"]["document_id"])
        self.room = f"collab_{self.document_id}"
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()
        await self.channel_layer.group_send(
            self.room,
            {
                "type": "collab.event",
                "payload": {
                    "type": "presence",
                    "action": "join",
                    "user": await self.user_payload(),
                    "at": timezone.now().isoformat(),
                },
            },
        )

    async def disconnect(self, code):
        if hasattr(self, "room"):
            await self.channel_layer.group_send(
                self.room,
                {
                    "type": "collab.event",
                    "payload": {
                        "type": "presence",
                        "action": "leave",
                        "user": await self.user_payload(),
                        "at": timezone.now().isoformat(),
                    },
                },
            )
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive_json(self, content, **kwargs):
        msg_type = content.get("type")
        payload = {
            "type": msg_type,
            "user": await self.user_payload(),
            "data": content.get("data", {}),
            "client_id": content.get("client_id"),
            "revision": content.get("revision"),
            "at": timezone.now().isoformat(),
        }
        if msg_type != "patch":
            await self.persist_awareness(content)
        await self.channel_layer.group_send(self.room, {"type": "collab.event", "payload": payload})

    async def collab_event(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def user_payload(self):
        u = self.user
        return {
            "id": str(u.id),
            "display_name": getattr(u, "full_name", None) or u.email,
            "avatar_url": getattr(u, "avatar_url", ""),
            "color": _color_for_user(str(u.id)),
        }

    @database_sync_to_async
    def persist_awareness(self, content):
        from apps.collaboration.models import CollaborationSession

        CollaborationSession.objects.update_or_create(
            entry_id=self.document_id,
            user=self.user,
            defaults={
                "client_id": content.get("client_id", ""),
                "cursor": content.get("data", {}).get("cursor", {}),
                "selection": content.get("data", {}).get("selection", {}),
                "last_seen_at": timezone.now(),
                "is_active": True,
            },
        )


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        self.group = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send_json(event["payload"])


def _color_for_user(user_id: str) -> str:
    palette = ["#C45C26", "#2F6F4E", "#1F4E79", "#8B3A3A", "#5C4B8A", "#B8860B", "#2E8B8B"]
    return palette[sum(ord(c) for c in user_id) % len(palette)]
