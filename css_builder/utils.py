
import re
import os

from django.conf import settings

here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)

def background2b64(path):
    """
    Create data streams for embedding image from background and
    background-image declarations.

    Parameters:
        path - relative path to the css file
    """
    f = open(os.path.join(settings.MEDIA_ROOT, path), "r")
    content = f.read()
    f.close()

    def background_image_to_b64_replace(matchobj):
        path = matchobj.groupdict()["path"]
        f = open(os.path.join(settings.MEDIA_ROOT, path), "r")
        content = f.read().encode("base64")
        f.close()
        return "background-image: url(data:image/png;base64,%s);" % content

    def background_to_b64_replace(matchobj):
        path = matchobj.groupdict()["path"]
        f = open(os.path.join(settings.MEDIA_ROOT, path), "r")
        content = f.read().encode("base64")
        f.close()
        return "background: %s url(data:image/png;base64,%s)%s;" %\
            (matchobj.groupdict()["bg_color"], content,
             matchobj.groupdict()["bg_properties"])

    new_content = re.sub(
                r"background-image: url\((?P<path>[^)]+)\); \/\* 2b64 \*\/",
                background_image_to_b64_replace, content)
    new_content = re.sub(
                r"background: (?P<bg_color>[^\s]*) url\((?P<path>[^)]+)\)" +\
                "(?P<bg_properties>[^;]*); \/\* 2b64 \*\/",
                background_to_b64_replace, new_content)
    f = open(path, "w")
    f.write(new_content)
    f.close()
