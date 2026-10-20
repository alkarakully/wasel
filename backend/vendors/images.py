"""Product photos: checked, turned upright, shrunk and saved as JPEG."""

import io
import uuid

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # nginx allows 5 MB request bodies
MAX_SIDE = 1200


class BadImage(Exception):
    def __init__(self, code, detail):
        super().__init__(detail)
        self.code, self.detail = code, detail


def save_product_image(product, upload):
    """Replaces the product's photo with `upload`; raises BadImage if it isn't a usable picture."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise BadImage("image_too_large", "Photos can be up to 5 MB.")
    try:
        picture = Image.open(upload)
        picture.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise BadImage("invalid_image", "That file isn't a photo we can use.") from error

    # Phones store rotation in EXIF; apply it, then drop EXIF (it can carry the location).
    picture = ImageOps.exif_transpose(picture)
    if picture.mode in ("RGBA", "LA", "P"):
        picture = picture.convert("RGBA")
        white = Image.new("RGB", picture.size, "white")
        white.paste(picture, mask=picture.getchannel("A"))
        picture = white
    else:
        picture = picture.convert("RGB")
    picture.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    picture.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    remove_product_image(product, save=False)
    product.image.save(f"{product.pk}-{uuid.uuid4().hex[:10]}.jpg", ContentFile(out.getvalue()), save=False)
    product.save(update_fields=["image"])


def remove_product_image(product, save=True):
    if product.image:
        product.image.delete(save=False)
        if save:
            product.save(update_fields=["image"])
