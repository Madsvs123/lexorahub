from channels.generic.websocket import AsyncJsonWebsocketConsumer


class UserNotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or user.is_authenticated:
            await self.close()
            return
        self.group = f"notifications_{user.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send_json(event["payload"])
