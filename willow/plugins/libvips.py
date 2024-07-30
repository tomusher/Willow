import functools
import pyvips

from willow.image import (
    AvifImageFile,
    BadImageOperationError,
    BMPImageFile,
    GIFImageFile,
    HeicImageFile,
    IcoImageFile,
    Image,
    JPEGImageFile,
    PNGImageFile,
    RGBAImageBuffer,
    RGBImageBuffer,
    TIFFImageFile,
    WebPImageFile,
)


class UnsupportedRotation(Exception):
    pass


def _libvips_errors():
    return pyvips.error


def _libvips_image():
    return pyvips.Image


class LibVipsImage(Image):
    def __init__(self, image):
        self.image = image

    @classmethod
    def check(cls):
        _libvips_image()

    def _clone(self):
        return LibVipsImage(self.image.copy())

    @classmethod
    def is_format_supported(cls, image_format):
        return bool(_wand_version().formats(image_format))

    @Image.operation
    def get_size(self):
        return (self.image.width, self.image.height)

    @Image.operation
    def get_frame_count(self):
        try:
            return self.image.get("n-pages")
        except _libvips_errors().Error:
            return 1

    @Image.operation
    def has_alpha(self):
        return self.image.hasalpha()

    @Image.operation
    def has_animation(self):
        return self.get_frame_count() > 1

    @Image.operation
    def resize(self, size):
        return LibVipsImage(self.image.thumbnail_image(size[0], height=size[1]))

    @Image.operation
    def crop(self, rect):
        left, top, right, bottom = rect
        width = self.image.width
        height = self.image.height
        if (
            left >= right
            or left >= width
            or right <= 0
            or top >= bottom
            or top >= height
            or bottom <= 0
        ):
            raise BadImageOperationError(f"Invalid crop dimensions: {rect!r}")

        left = max(0, left)
        top = max(0, top)
        crop_width = right - left if right < width else width - left
        crop_height = bottom - top if bottom < height else height - top

        return LibVipsImage(self.image.crop(left, top, crop_width, crop_height))

    @Image.operation
    def rotate(self, angle):
        return LibVipsImage(self.image.rotate(angle))

    @Image.operation
    def set_background_color_rgb(self, color):
        if not self.has_alpha():
            # Don't change image that doesn't have an alpha channel
            return self

        # Check type of color
        if not isinstance(color, (tuple, list)) or not len(color) == 3:
            raise TypeError("the 'color' argument must be a 3-element tuple or list")

        return LibVipsImage(self.image.flatten(background=color))

    def get_icc_profile(self):
        return self.image.get("icc-profile-data")

    def get_exif_data(self):
        return self.image.get("exif-data")

    @Image.operation
    def save_as_jpeg(
        self,
        f,
        quality: int = 85,
        progressive: bool = False,
        apply_optimizers: bool = True,
        **kwargs,
    ):
        """
        Save the image as a JPEG file.

        :param f: the file or file-like object to save to
        :param quality: the image quality
        :param progressive: whether to save as progressive JPEG file.
        :param apply_optimizers: controls whether to run any configured optimizer libraries
        :return: JPEGImageFile
        """
        f.write(self.image.write_to_buffer(".jpeg", Q=quality, interlace=progressive))
        # TODO: copy ICC and EXIF profile data

        if apply_optimizers:
            self.optimize(f, "jpeg")
        return JPEGImageFile(f)

    @Image.operation
    def save_as_png(self, f, apply_optimizers: bool = True, **kwargs):
        """
        Save the image as a PNG file.

        :param f: the file or file-like object to save to
        :param apply_optimizers: controls whether to run any configured optimizer libraries
        :return: PNGImageFile
        """
        f.write(self.image.write_to_buffer(".png"))

        if apply_optimizers:
            self.optimize(f, "png")
        return PNGImageFile(f)

    @Image.operation
    def save_as_gif(self, f, apply_optimizers: bool = True):
        f.write(self.image.write_to_buffer(".gif"))

        if apply_optimizers:
            self.optimize(f, "gif")
        return GIFImageFile(f)

    @Image.operation
    def save_as_webp(
        self,
        f,
        quality: int = 80,
        lossless: bool = False,
        apply_optimizers: bool = True,
    ):
        """
        Save the image as a WEBP file.

        :param f: the file or file-like object to save to
        :param quality: the image quality
        :param lossless: whether to save as lossless WEBP file.
        :param apply_optimizers: controls whether to run any configured optimizer libraries.
            Note that when lossless=True, this will be ignored.
        :return: WebPImageFile
        """
        f.write(self.image.write_to_buffer(".webp", Q=quality, lossless=lossless))
        # TODO: Copy ICC profile

        if not lossless and apply_optimizers:
            self.optimize(f, "webp")
        return WebPImageFile(f)

    @Image.operation
    def save_as_avif(self, f, quality=80, lossless=False, apply_optimizers=True):
        f.write(self.image.write_to_buffer(".avif", Q=quality, lossless=lossless))

        if not lossless and apply_optimizers:
            self.optimize(f, "avif")

        return AvifImageFile(f)

    @Image.operation
    def save_as_ico(self, f, apply_optimizers=True):
        f.write(self.image.magicksave_buffer(format="ico"))

        if apply_optimizers:
            self.optimize(f, "ico")

        return IcoImageFile(f)

    @Image.operation
    def auto_orient(self):
        return self.image.autorot()

    @Image.operation
    def get_libvips_image(self):
        return self.image

    @classmethod
    @Image.converter_from(JPEGImageFile, cost=50)
    @Image.converter_from(PNGImageFile, cost=50)
    @Image.converter_from(GIFImageFile, cost=50)
    @Image.converter_from(BMPImageFile, cost=50)
    @Image.converter_from(TIFFImageFile, cost=50)
    @Image.converter_from(WebPImageFile, cost=50)
    @Image.converter_from(HeicImageFile, cost=50)
    @Image.converter_from(AvifImageFile, cost=50)
    @Image.converter_from(IcoImageFile, cost=50)
    def open(cls, image_file):
        image_file.f.seek(0)
        libvips_image = _libvips_image()
        image = libvips_image.new_from_buffer(image_file.f.read(), "")

        return cls(image)


willow_image_classes = [LibVipsImage]
