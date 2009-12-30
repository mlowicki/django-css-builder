
import os
import re
import commands
import logging
from contextlib import closing

from django.conf import settings
from django import template
from django.utils import importlib

from css_builder.core_utils import (get_package_files,
                                    concatenate_package_files,
                                    find_package_files,)
from css_builder.models import SpriteImage, Sprite

here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), *x)

try:
    mod = importlib.import_module(settings.SETTINGS_MODULE)
except ImportError, e:
    raise ImportError, "Could not import settings '%s': %s" % \
                                    (settings.SETTINGS_MODULE, e)
                                    
LOG_FILENAME = os.path.join(os.path.dirname(mod.__file__), "css_builder.log")
BASIC_FORMAT = "%(asctime)s - %(name)-20s - %(levelname)s - %(message)s" 

format = getattr(settings, "CSS_BUILDER_FORMAT", BASIC_FORMAT)

LOG_FILE = logging.StreamHandler(open(LOG_FILENAME, "a"))
LOG_FILE.setLevel(logging.ERROR)
LOG_FILE.setFormatter(logging.Formatter(format))

CONSOLE = logging.StreamHandler()
CONSOLE.setLevel(logging.ERROR)
CONSOLE.setFormatter(logging.Formatter(format))

STREAM_HANDLERS = [CONSOLE, LOG_FILE]

def log(logger_name, msg):
    for sh in STREAM_HANDLERS:
        logging.getLogger(logger_name).removeHandler(sh)

    for sh in getattr(settings, "CSS_BUILDER_LOGGING", [LOG_FILE]):
        logging.getLogger(logger_name).addHandler(sh)
    logging.getLogger(logger_name).error(msg)

    if getattr(settings, "CSS_BUILDER_EXCEPTION", False):
        raise Exception("%s : %s" % (logger_name, msg))

BACKGROUND_REPEAT = r"(?P<bg_repeat>(repeat)|(no-repeat)|(repeat-x)|(repeat-y))"
# TODO: add color names like green, yellow etc
BACKGROUND_COLOR = r"(?P<bg_color>((#[a-fA-F0-9]{6})|(#[a-fA-F0-9]{3})|(red)))"
BACKGROUND_POSITION = r"(?P<bg_position>[a-zA-Z0-9-%]+\ +[a-zA-Z0-9-%]+)"
BACKGROUND_IMAGE = r"(?P<bg_image>url\((?P<bg_image_url>[^)]+)\))"

BACKGROUND = r"background:\s+%s\s+%s\s+%s\s+%s\s*;" % (BACKGROUND_COLOR,
                    BACKGROUND_IMAGE, BACKGROUND_REPEAT, BACKGROUND_POSITION) 
BACKGROUND_SPRITE = BACKGROUND + r"\s*\/\*\s*2sprite\s*\*\/\s*"
BACKGROUND_B64 = BACKGROUND + r"\s*\/\*\s*2b64\s*\*\/\s*"
BACKGROUND_SHORT = r"background-image:\s+%s\s*;" % BACKGROUND_IMAGE
BACKGROUND_SHORT_SPRITE = BACKGROUND_SHORT + r"\s*\/\*\s*2sprite\s*\*\/\s*"
BACKGROUND_SHORT_B64 = BACKGROUND_SHORT + r"\s*\/\*\s*2b64\s*\*\/\s*"


def check_basic_config():
    """
    Check if CSS_BUILDER_* are set and correct
    """
    success = True
    if not hasattr(settings, "CSS_BUILDER_DEST"):
        log("check_basic_config", "CSS_BUILDER_DEST is not set")
        success = False
    else:
        if not os.path.exists(settings.CSS_BUILDER_DEST):
            log("check_basic_config",
                "Destination directory does not exist: %s" %\
                settings.CSS_BUILDER_DEST)
            success = False
    if not hasattr(settings, "CSS_BUILDER_SOURCE"):
        log("check_basic_config", "CSS_BUILDER_SOURCE is not set")
        success = False
    else:
        if not os.path.exists(settings.CSS_BUILDER_SOURCE):
            log("check_basic_config", "Source directory does not exist: %s" %
                                                settings.CSS_BUILDER_SOURCE)
            success = False
    #if not hasattr(settings, "CSS_BUILDER_PACKAGES"):
    #    log("check_config", "CSS_BUILDER_PACKAGES is not set")
    #    success = False
    return success


def package_needs_rebuilding(files, package_name):
    """
    TODO
        check if some files were added since last building
    """
    package_file = os.path.join(
                            settings.CSS_BUILDER_DEST, package_name + ".css")
    if not os.path.exists(package_file):
        return True
    package_m_time = os.path.getmtime(package_file)
    for f in files:
        if os.path.getmtime(f) > package_m_time:
            return True
    return False

def build_package(package_name, check_configuration=True, **options):
    """
    Build package 'package_name'

    Parameters:
        package_name <str>
        check_configuration <bool>
    """
    if check_configuration:
        if check_basic_config() == False:
            return
    if not package_name in settings.CSS_BUILDER_PACKAGES:
        log("build_package", "Unknown package: %s" % package_name)
    else:
        try:
            compress = options.get("compress", False)
            files, dependencies = get_package_files(
                                settings.CSS_BUILDER_PACKAGES[package_name],
                                settings.CSS_BUILDER_SOURCE)

            if package_needs_rebuilding(files, package_name):
                output = os.path.join(settings.CSS_BUILDER_DEST,
                                      package_name + ".css")
                concatenate_package_files(output, dependencies)
                add_css_sprites(output)
                add_embedding_images(output)
                if compress:
                    compress_package(package_name)
            else:
                if compress and not os.path.exists(os.path.join(
                        settings.CSS_BUILDER_DEST, package_name + "-min.css")):
                    compress_package(package_name)
        except Exception, e:
            log("build_package", *e)


def found_css_sprite(path):
    """
    Return sprite which path belongs for

    Parameters:
        path <str> - absolute path to the file
    Return:
        None or <str>
    """
    if not hasattr(settings, "CSS_BUILDER_SPRITES"):
        log("found_css_sprite", "CSS_BUILDER_SPRITES is not set")
        return None

    for sprite in settings.CSS_BUILDER_SPRITES:
        
        files = find_package_files(settings.CSS_BUILDER_SPRITES[sprite]["files"],
                                   settings.CSS_BUILDER_SOURCE)
        if path in files:
            return sprite
    log("found_css_sprite", "CSS sprite for %s not found" % path)
    return None


def get_css_sprite_data(path):
    """
    Parameters:
        path <str> - relative path
    """
    abspath = os.path.join(settings.CSS_BUILDER_SOURCE, path)
    sprite_name = found_css_sprite(abspath)
    if sprite_name == None:
        return None
    if not css_sprite_is_up_to_date(sprite_name):
        if not build_css_sprite(sprite_name):
            return None
    image = SpriteImage.objects.get(path = abspath)
    if not os.path.exists(abspath):
        log("get_css_sprite_data", "%s (%s) does not exists." % (path, abspath))
        return None

    return {"bg_image_url": sprite_name, "bg_x": "%dpx" % image.x,
            "bg_y": "%dpx" % image.y}


def add_css_sprites(path, all=False):
    """
    Replace path in background and background-image rules by path to the
    sprite image and add correct background position.

    Parameters:
        path <str>    - absolute path to the input file
        all <bool>    - indicates if only add css sprite to the rules with
                        comment /* 2sprite */ at the end line or to all
                        background-images styles
    """
    if not check_basic_config():
        return

    with closing(open(path, "r")) as f:
        content = f.read()

    def to_sprite(matchobj):
        data = matchobj.groupdict()
        sprite_data = get_css_sprite_data(data["bg_image_url"])
        if sprite_data == None:
            # TODO
            return "background: none;"
        return "background: %s url(%s) %s %s %s;" % (data["bg_color"],
                                sprite_data["bg_image_url"], data["bg_repeat"],
                                sprite_data["bg_x"], sprite_data["bg_y"])

    with closing(open(path, "w")) as f:
        if all==True:
            f.write(re.sub(BACKGROUND, to_sprite, content))
        else:
            f.write(re.sub(BACKGROUND_SPRITE, to_sprite, content))


def add_embedding_images(path):
    """
    Create data streams for embedding image from background and
    background-image styles.

    Parameters:
        path <str> - absolute path to the input file
    """
    f = open(path, "r")
    content = f.read()
    f.close()

    def background_image_to_b64(matchobj):
        data = matchobj.groupdict()
        f = open(os.path.join(settings.CSS_BUILDER_SOURCE,
                              data["bg_image_url"]), "r")
        content_b64 = f.read().encode("base64")
        f.close()
        root, ext = os.path.splitext(data["bg_image_url"])
        return "background-image: url(data:image/%s;base64,%s);" %\
                                                            (ext[1:], content_b64)

    def background_to_b64(matchobj):
        data = matchobj.groupdict()
        f = open(os.path.join(settings.CSS_BUILDER_SOURCE,
                              data["bg_image_url"]), "r")
        content_b64 = f.read().encode("base64")
        f.close()
        root, ext = os.path.splitext(data["bg_image_url"])
        return "background: %s url(data:image/%s;base64,%s) %s %s;" %\
            (data["bg_color"], ext[1:], content_b64, data["bg_repeat"],
             data["bg_position"],)

    new_content = re.sub(BACKGROUND_SHORT_B64, background_image_to_b64, content)
    new_content = re.sub(BACKGROUND_B64, background_to_b64, new_content)

    f = open(path, "w")
    f.write(new_content)
    f.close()


def build_all_packages(**options):
    """
    Build all packages from CSS_BUILDER_PACKAGEs
    """
    if check_basic_config():
        for sprite_name in settings.CSS_BUILDER_PACKAGES:
            build_package(sprite_name, False, **options)

def compress_package(package_name):
    """
    Compress package file

    Parameters:
        package_name <str>
    """
    in_file = os.path.join(settings.CSS_BUILDER_DEST, package_name + ".css")
    out_file = os.path.join(settings.JS_BUILDER_DEST, package_name + "-min.css")
    command = "java -jar %s %s -o %s" % (here(("yuicompressor-2.4.2",
                                "yuicompressor-2.4.2.jar",)), in_file, out_file)
    status, output = commands.getstatusoutput(command)
    if status != 0:
        log("yui compressor", error(output))


class ImageFile(object):
    """
    Class represents image
    """
    def __init__(self, path):
        """
        Parameters:
            path <str> - absolute path to the image file
            width <int> - image width
            height <int> - image height
            
        """
        self.path = path
        # TODO: get image size
        self.width = 100
        self.height = 200


class SpriteImageFile(ImageFile):
    """
    Class represents sprite image
    """
    def __init__(self, path, x, y):
        """
        Parameters:
            path <str> - absolute path to the image file
            width <int> - image width
            height <int> - image height
            x <int> - TODO
            y <int> - TODO
            
        """
        super(SpriteImageFile, self).__init__(path)
        self.x = x
        self.y = y


def build_css_sprite_vertically(images):
    """
    Compute position of each part image in css sprite.

    Parameters:
        images [Image]
    Return:
        [SpriteImage]
    """
    results = []
    current_y = 0
    for image in images:
        sprite_image = SpriteImageFile(image.path, 0, current_y)
        results.append(sprite_image)
        if current_y == 0:
            current_y += 1
        current_y += image.height
    return results


def build_css_sprite_horizontaly(images):
    """
    Compute position of each part image in css sprite.

    Parameters:
        images [Image]
    Return:
        [SpriteImage]
    """
    results = []
    current_x = 0
    for image in images:
        sprite_image = SpriteImageFile(image.path, current_x, 0)
        results.append(sprite_image)
        if current_x == 0:
            current_x += 1
        current_x += image.width
    return results


def build_css_sprite_default(images):
    """
    Compute position of each part image in css sprite.

    Parameters:
        images [Image]
    Return:
        [SpriteImage]
    """
    pass


def create_css_sprite_file(sprite_name, images):
    """
    Create css sprite file and appropriate object in database.
    
    Parameters:
        sprite_name <str>
        images [SpriteImage]
    """
    if len(images) == 0:
        return
    # TODO: create sprite file
    try:
        sprite = Sprite.objects.get(name=sprite_name)
    except Sprite.DoesNotExist:
        sprite = Sprite.objects.create(name=sprite_name)

    sprite_cfg = settings.CSS_BUILDER_SPRITES[sprite_name]
    sprite.orientation = sprite_cfg.get("orientation", "default")
    sprite.save()
 
    for image in images:
        try:
            sprite_image = SpriteImage.objects.get(path=image.path,
                                                      sprite=sprite)
        except SpriteImage.DoesNotExist:
            sprite_image = SpriteImage(path=image.path, sprite=sprite)
        sprite_image.x = image.x
        sprite_image.y = image.y
        sprite_image.save()


def build_css_sprite(sprite_name):
    """
    Create sprite file.

    Parameters:
        sprite_name <str>
    Return:
        bool
    """
    cfg = settings.CSS_BUILDER_SPRITES[sprite_name]
    paths = find_package_files(cfg["files"], settings.CSS_BUILDER_SOURCE)
    images = []
    for path in paths:
        images.append(ImageFile(path))
    if cfg.has_key("orientation"):
        if cfg["orientation"] == "vertically":
            sprite_images = build_css_sprite_vertically(images)
        elif cfg["orientation"] == "horizontaly":
            sprite_images = build_css_sprite_horizontaly(images)
        else:
            log("build_css_sprite", "Unrecognized orientation: %s" %\
                cfg["orientation"])
            return False
    else:
        sprite_images = build_css_sprite_default(images)
    create_css_sprite_file(sprite_name, sprite_images)
    return True


def css_sprite_is_up_to_date(sprite_name):
    """
    Checks if sprite file needs rebuild

    Parameters:
        sprite_name <str>
    Retrun:
        bool
    """
    cfg = settings.CSS_BUILDER_SPRITES[sprite_name]
    current_files = find_package_files(cfg["files"],
                                       settings.CSS_BUILDER_SOURCE)
    sprite_file = os.path.join(settings.CSS_BUILDER_DEST, sprite_name)

    if not os.path.exists(sprite_file): # sprite files doesn't exist
        return False

    try:
        sprite = Sprite.objects.get(name=sprite_name)
    except Sprite.DoesNotExist:
        return False

    # check if orientation property wasn't changed
    if cfg.get("orientation", "default") != sprite.orientation:
        return False

    sprite_part_files = sprite.images.all()

    for f in sprite_part_files:
        if not os.path.exists(f.path): # file has been removed
            return False
        # some file from css sprite files has been modified
        sprite_m_time = os.path.getmtime(sprite_file)
        if os.path.getmtime(f.path) > sprite_m_time:
            return False
    for f in current_files: # check if new files have been added
        try:
            SpriteImage.objects.get(path = f, sprite = sprite)
        except SpriteImage.DoesNotExist:
            return False
    return True
