
import re
import os

from django.conf import settings

here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)

def img2b64(path):
    """
    Replace background-image: url(IMAGE.png); with
    background-image: url(data:image/png;base64,B64_FROM_IMAGE);
    """
    f = open(os.path.join(settings.MEDIA_ROOT, path), "r")
    content = f.read()
    f.close()

    def path_to_b64_replace(matchobj):
        path = matchobj.groupdict()["path"]
        f = open(os.path.join(settings.MEDIA_ROOT, path), "r")
        content = f.read()
        f.close()
        return "background-image: url(data:image/png;base64,%s);" %\
            content.encode("base64")
    pattern = "background-image: url\((?P<path>[^)]+)\); \/\* 2b64 \*\/"
    new_content= re.sub(pattern, path_to_b64_replace, content)
    f = open(path, "w")
    f.write(new_content)
    f.close()