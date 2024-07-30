import io
from willow.image import JPEGImageFile
from willow.registry import registry


def test_libvips_resize_reformat():
    with open("tests/images/large_image.jpg", "rb") as f:
        image = JPEGImageFile.open(f)
        resized = image.resize((100, 100))
        output = io.BytesIO()
        resized.save_as_webp(output)


if __name__ == "__main__":
    import timeit
    import resource

    print(timeit.timeit("test_libvips_resize_reformat()", globals=locals(), number=100))
    resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
