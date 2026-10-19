from celery import shared_task
from django.core.files.base import ContentFile
from PIL import Image
import io


def detect_asset_type(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    if mime in {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        return "document"
    return "other"


RENDITIONS = {
    "thumb": (200, 200),
    "medium": (800, 800),
    "large": (1600, 1600),
    "og": (1200, 630),
}


@shared_task(name="media.generate_image_renditions")
def generate_image_renditions(asset_id: str):
    from apps.media_library.models import MediaAsset, MediaTransformation

    try:
        asset = MediaAsset.objects.get(pk=asset_id)
    except MediaAsset.DoesNotExist:
        return

    if asset.asset_type != MediaAsset.AssetType.IMAGE or not asset.file:
        return

    asset.file.open("rb")
    try:
        img = Image.open(asset.file)
        img.load()
    finally:
        asset.file.close()

    for name, (max_w, max_h) in RENDITIONS.items():
        copy = img.copy()
        copy.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        fmt = "JPEG" if copy.mode in ("RGB", "L") else "PNG"
        if copy.mode == "RGBA" and fmt == "JPEG":
            copy = copy.convert("RGB")
        copy.save(buf, format=fmt, quality=85)
        buf.seek(0)
        filename = f"{asset.id}_{name}.{fmt.lower()}"
        transform, _ = MediaTransformation.objects.update_or_create(
            asset=asset,
            name=name,
            defaults={
                "width": copy.width,
                "height": copy.height,
                "mime_type": f"image/{fmt.lower()}",
                "file_size": buf.getbuffer().nbytes,
                "params": {"max_width": max_h, "max_height": max_w},
            },
        )
        transform.file.save(filename, ContentFile(buf.read()), save=True)
