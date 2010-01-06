"""
"""

#
# TODO: during tests change log file
#

import os
import shutil
import re
import time

from django.test import TestCase
from django.conf import settings
from django import template
from django.http import HttpRequest

from css_builder.utils import (add_embedding_images, add_css_sprites, here,
                               BACKGROUND_REPEAT, BACKGROUND_COLOR,
                               BACKGROUND_POSITION, BACKGROUND,
                               BACKGROUND_IMAGE, build_package,
                               build_css_sprite, ImageFile, SpriteImageFile,
                               css_sprite_is_up_to_date, text_2_b64,
                               found_css_sprite, create_css_sprite_file,
                               get_sprite_format, IMAGE_FORMATS)
from css_builder.tests_utils import SettingsTestCase, check_last_log
from css_builder.models import SpriteImage, Sprite

class UtilsTest(SettingsTestCase):
    """
    TODO:
        tests for checking if right files are created according to
        GET, JS_BUILDER_COMPERSS and DEBUG values
    """
    def setUp(self):
        self.rootTestsDir = here(["tests_data"])
        if os.path.isdir(self.rootTestsDir):
            shutil.rmtree(self.rootTestsDir)
        os.mkdir(self.rootTestsDir)

    def tearDown(self):
        super(UtilsTest, self).tearDown()
        shutil.rmtree(self.rootTestsDir)
        for sprite in Sprite.objects.all():
            sprite.delete()
        for image in SpriteImage.objects.all():
            image.delete()

    def test_regexps(self):
        self.failIfEqual(re.match(BACKGROUND_REPEAT, "repeat"), None)
        self.failIfEqual(re.match(BACKGROUND_REPEAT, "no-repeat"), None)
        self.failIfEqual(re.match(BACKGROUND_REPEAT, "repeat-x"), None)
        self.failIfEqual(re.match(BACKGROUND_REPEAT, "repeat-y"), None)
        self.failUnlessEqual(re.match(BACKGROUND_REPEAT, " repeat"), None)

        self.failIfEqual(re.match(BACKGROUND_COLOR, "#808080"), None)
        self.failIfEqual(re.match(BACKGROUND_COLOR, "#ABC123"), None)
        self.failIfEqual(re.match(BACKGROUND_COLOR, "#18A"), None)
        self.failIfEqual(re.match(BACKGROUND_COLOR, "#ABC"), None)
        self.failUnlessEqual(re.match(BACKGROUND_COLOR, "#00"), None)

        self.failIfEqual(re.match(BACKGROUND_POSITION, "center center"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "top left"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "top center"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "top right"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "center right"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "bottom center"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "bottom   left"), None)

        self.failIfEqual(re.match(BACKGROUND_POSITION, "50% 50%"), None)
        self.failIfEqual(re.match(BACKGROUND_POSITION, "-100px -50px"), None)
       
        self.failIfEqual(re.match(BACKGROUND_IMAGE, 
                                            "url(/static_media/a.jpg)"),None)
        self.failIfEqual(re.match(BACKGROUND, 
            "background: #808080 url(/static_media/a.jpg) no-repeat top left;"),
             None)

    def test_add_css_sprites(self):
        os.mkdir(os.path.join(self.rootTestsDir, 'source'))
        os.mkdir(os.path.join(self.rootTestsDir, 'dest'))
        css_file = os.path.join(self.rootTestsDir, 'source', 't.css')
        f = open(css_file, 'w')
        f.write(
            'background: #808080 url(a.png) no-repeat top left; /* 2sprite */')
        f.close()
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(self.rootTestsDir, 'source', 'a.png'))
        
        self.settings_manager.remove(['CSS_BUILDER_SOURCE'])
        add_css_sprites(css_file)
        self.failUnless(check_last_log('CSS_BUILDER_SOURCE is not set'))
        self.settings_manager.set(
                CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, 'source'),
                MEDIA_ROOT='')
        add_css_sprites(css_file)
        self.failUnless(check_last_log('MEDIA_ROOT directory does not exist'))

        self.settings_manager.set(
                MEDIA_ROOT=os.path.join(self.rootTestsDir, 'dest'),
                CSS_BUILDER_SPRITES={'s1': {'files': [r'.*\.png'],
                                            'orientation': 'vertically'}})

        add_css_sprites(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
                'background: #808080 url(%s) no-repeat 0px 0px;' %\
                os.path.join(settings.MEDIA_URL, 's1.PNG'))

        f = open(css_file, 'w')
        f.write(
            'background: #808080 url(a.png) no-repeat top left;')
        f.close()
        add_css_sprites(css_file, all=True)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
                'background: #808080 url(%s) no-repeat 0px 0px;' %\
                os.path.join(settings.MEDIA_URL, 's1.PNG'))

        add_css_sprites(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
            'background: #808080 url(%s) no-repeat 0px 0px;' %\
            os.path.join(settings.MEDIA_URL, 's1.PNG'))

        self.settings_manager.set(
                            CSS_BUILDER_SPRITES={'s1': {'files': [r'.*\.png'],
                                            'orientation': 'wrong name'}})
        f = open(css_file, 'w')
        f.write(
            'background: #808080 url(a.png) no-repeat top left; /* 2sprite */')
        f.close()

        add_css_sprites(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content, 'background: none;')

    def test_add_embedding_images(self):
        self.settings_manager.set(
                CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, 'source'),
                MEDIA_URL='/site_media/',
                MEDIA_ROOT=os.path.join(self.rootTestsDir, 'dest'))
        os.mkdir(settings.MEDIA_ROOT)
        os.mkdir(settings.CSS_BUILDER_SOURCE)
        f = open(os.path.join(settings.MEDIA_ROOT, 'a.png'), 'w')
        f.write('abcdef')
        f.close()
        css_file = os.path.join(settings.CSS_BUILDER_SOURCE, 't.css')
        f = open(css_file, "w")
        f.write('background-image: url(/site_media/a.png); /* 2b64 */')
        f.close()
        add_embedding_images(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
                        'background-image: url("data:image/png;base64,%s");' %\
                        text_2_b64('abcdef'))

        f = open(os.path.join(settings.MEDIA_ROOT, 'a.jpg'), 'w')
        f.write('abcdefghij')
        f.close()
        f = open(css_file, "w")
        c = 'background: #808080 url(/site_media/a.jpg)'
        c += ' no-repeat 0px 0px; /*2b64*/'
        f.write(c)
        f.close()
        add_embedding_images(css_file)
        f = open(css_file, "r")
        content = f.read()
        f.close()
        self.failUnlessEqual(content,'background: #808080 url("data:image/jpg;\
base64,%s") no-repeat 0px 0px;' % text_2_b64('abcdefghij'))

        f = open(css_file, 'w')
        f.write('background: red url("/site_media/a.png") no-repeat top left;\
/* 2b64 */ ')
        f.close()
        add_embedding_images(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content,'background: red url("data:image/png;\
base64,%s") no-repeat top left;' % text_2_b64('abcdef'))

        f = open(css_file, 'w')
        f.write('background: red url(/site_media/a.png) no-repeat top left;\
  /* 2b64  */  ')
        f.close()
        add_embedding_images(css_file)
        f = open(css_file, 'r')
        content = f.read()
        f.close()
        self.failUnlessEqual(content, 'background: red url("data:image/png;\
base64,%s") no-repeat top left;' % text_2_b64('abcdef'))

    def test_get_sprite_format(self):
        self.settings_manager.set(
            MEDIA_ROOT=os.path.join(self.rootTestsDir, 'dest'),
            CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, 'source'))
        os.mkdir(settings.MEDIA_ROOT)
        os.mkdir(settings.CSS_BUILDER_SOURCE)
        
        self.settings_manager.set(
            CSS_BUILDER_SPRITES={'s1': {'files': ['.*\.png'],
                'orientation': 'vertically', 'format': 'wrong'}})
        self.failUnlessEqual(get_sprite_format('s1'), None)
        self.failUnless(check_last_log('get_sprite_format'))
        self.failUnless(
            check_last_log('Unrecognized image format %s in sprite %s \
definition. Available formats: %s' % ('wrong', 's1', IMAGE_FORMATS)))

        self.settings_manager.set(
            CSS_BUILDER_SPRITES={'s1': {'files': ['.*\.png'],
                'orientation': 'vertically', 'format': 'jpg'}})
        self.failUnlessEqual(get_sprite_format('s1'), 'JPG')
        
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'a.png'))
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'b.png'))
        self.settings_manager.set(
            CSS_BUILDER_SPRITES={'s1': {'files': ['.*\.(png|jpg)'],
                'orientation': 'vertically'}})
        self.failUnlessEqual(get_sprite_format('s1'), 'PNG')

        shutil.copyfile(here(['tests_files', 'b.jpg']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'c.jpg'))
        self.failUnlessEqual(get_sprite_format('s1'), None)
    
        f = open(os.path.join(settings.CSS_BUILDER_SOURCE, 'd.jpg'), 'w')
        f.close()
        self.failUnlessEqual(get_sprite_format('s1'), None)
        self.failUnless(check_last_log('get_sprite_format'))
        self.failUnless('Unreconized image format %s. Available formats: %s' %\
            ('None', IMAGE_FORMATS))

    def test_build_css_sprite(self):
        self.settings_manager.set(
            MEDIA_ROOT=os.path.join(self.rootTestsDir, 'dest'),
            CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, 'source'),
            CSS_BUILDER_SPRITES={'p1': {'files': [r'.*\.png'],
                                        'orientation': 'vertically'}})

        os.mkdir(os.path.join(self.rootTestsDir, "source"))
        os.mkdir(os.path.join(self.rootTestsDir, "dest"))
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'a.png'))
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'b.png'))
        shutil.copyfile(here(['tests_files', 'a.png']),
            os.path.join(settings.CSS_BUILDER_SOURCE, 'c.png'))
        build_css_sprite('p1')
        coords = [[0,0], [0, 17], [0, 33]]
        for image in SpriteImage.objects.all():
            image_xy = [image.x, image.y]
            self.failUnless(image_xy in coords)
            coords.remove(image_xy)

        self.settings_manager.set(
                            CSS_BUILDER_SPRITES={'p1': {'files': [r'.*\.png'],
                                                'orientation': 'horizontaly'}})
        build_css_sprite('p1')
        coords = [[0,0], [17, 0], [33, 0]]
        for image in SpriteImage.objects.all():
            image_xy = [image.x, image.y]
            self.failUnless(image_xy in coords)
            coords.remove(image_xy)

        self.settings_manager.set(
                            CSS_BUILDER_SPRITES={'p1': {'files': [r'.*\.png'],
                                                'orientation': 'wrong name'}})
        build_css_sprite('p1')
        self.failUnless(check_last_log('Unrecognized orientation: wrong name'))

    def test_found_css_sprite(self):
        self.settings_manager.set(
                MEDIA_ROOT=os.path.join(self.rootTestsDir, "dest"),
                CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, "source"),
                CSS_BUILDER_PACKAGES={})
        os.mkdir(os.path.join(self.rootTestsDir, "source"))
        os.mkdir(os.path.join(self.rootTestsDir, "dest"))
        f = open(os.path.join(self.rootTestsDir, "source", "a.png"), "w")
        f.close()
        f = open(os.path.join(self.rootTestsDir, "source", "b.jpg"), "w")
        f.close()
        os.mkdir(os.path.join(self.rootTestsDir, "source", "d1"))
        f = open(os.path.join(self.rootTestsDir, "source", "d1", "c.png"), "w")
        f.close()
        f = open(os.path.join(self.rootTestsDir, "source", "d1", "d.jpg"), "w")
        f.close()
        os.mkdir(os.path.join(self.rootTestsDir, "source", "d1", "d2"))
        f = open(os.path.join(
                    self.rootTestsDir, "source", "d1", "d2", "e.bmp"), "w")
        f.close()
        self.settings_manager.remove(['CSS_BUILDER_SPRITES'])
        self.failUnlessEqual(found_css_sprite(os.path.join(
                            self.rootTestsDir, "source", "d1", "c.png")), None)
        self.failUnless(check_last_log("CSS_BUILDER_SPRITES is not set"))

        self.settings_manager.set(
                CSS_BUILDER_SPRITES={"a": {"files": [r"***/.*\.(png|jpg|bmp)"],
                                           "orientation": "horizontaly"}})

        p = os.path.join(self.rootTestsDir, "source", "d1", "d2",
                                                                "wrong_name.")
        self.failUnlessEqual(found_css_sprite(p), None)
        self.failUnless(check_last_log("CSS sprite for %s not found" % p))

        self.failUnlessEqual(found_css_sprite(os.path.join(
                            self.rootTestsDir, "source", "d1", "c.png")), "a")
        self.failUnlessEqual(found_css_sprite(os.path.join(
                            self.rootTestsDir, "source", "d1", "d.jpg")), "a")
        self.failUnlessEqual(found_css_sprite(os.path.join(
                    self.rootTestsDir, "source", "d1", "d2", "e.bmp")), "a")

    def test_css_sprite_is_up_to_date(self):
        self.settings_manager.set(
                MEDIA_ROOT=os.path.join(self.rootTestsDir, "dest"),
                CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, "source"),
                CSS_BUILDER_SPRITES={"p1": {"files": [r".*\.jpg"]}})
        os.mkdir(os.path.join(self.rootTestsDir, "source"))
        os.mkdir(os.path.join(self.rootTestsDir, "dest"))
        # sprite file does not exist
        self.failIf(css_sprite_is_up_to_date("p1"))

        f = open(os.path.join(self.rootTestsDir, "dest", "p1"), "w")
        f.close()
        # record in Sprite does not exist
        self.failIf(css_sprite_is_up_to_date("p1"))

        self.sprite_1 = Sprite.objects.create(name="p1")
        self.failUnless(css_sprite_is_up_to_date("p1"))

        # image exists in database but the file in the file system not
        SpriteImage.objects.create(sprite=self.sprite_1,
            path=os.path.join(self.rootTestsDir, "dest", "a.jpg"), x=0, y=0)
        self.failIf(css_sprite_is_up_to_date("p1"))
        # file modified after last building
        time.sleep(2)
        f = open(os.path.join(self.rootTestsDir, "dest", "a.jpg"), "w")
        f.close()
        self.failIf(css_sprite_is_up_to_date("p1"))
        # update outuput sprite file
        f = open(os.path.join(self.rootTestsDir, "dest", "p1"), "w")
        f.close()
        # new file has been added
        f = open(os.path.join(self.rootTestsDir, "source", "b.jpg"), "w")
        f.close()
        self.failIf(css_sprite_is_up_to_date("p1"))

    def test_css_file(self):
        source_path = os.path.join(self.rootTestsDir, 'source')
        dest_path = os.path.join(self.rootTestsDir, 'dest')
        os.mkdir(source_path)
        os.mkdir(dest_path)
        self.settings_manager.set(
                CSS_BUILDER_SOURCE=source_path,
                MEDIA_ROOT=dest_path,
                MEDIA_URL='/site_media/',
                DEBUG=True)

        os.mkdir(os.path.join(source_path, 'a'))
        t = template.Template('{% load css_tags %}{% css_file "a/b.css" %}')
        c = template.Context({})
        f = open(os.path.join(source_path, 'a', 'b.css'), 'w')
        f.write('div#a { position: absolute; }')
        f.close()
        self.failUnlessEqual(t.render(c), '<link rel="stylesheet" \
type="text/css" href="/site_media/a/b.css" />')

        t = template.Template('{% load css_tags %}{% css_file "a/c.css" %}')
        c = template.Context({})
        msg = '%s (%s) does not exists.' % ('a/c.css',
                        os.path.join(settings.CSS_BUILDER_SOURCE, 'a/c.css'))
        self.failUnlessEqual(t.render(c), '<!--\n%s\n-->' % msg)
        self.failUnless(check_last_log(msg))

    def test_css_package(self):
        source_path = os.path.join(self.rootTestsDir, 'source')
        dest_path = os.path.join(self.rootTestsDir, 'dest')
        os.mkdir(source_path)
        os.mkdir(dest_path)
        self.settings_manager.set(
                CSS_BUILDER_PACKAGES={'p1': ['.*\.css']},
                CSS_BUILDER_SOURCE=source_path,
                MEDIA_ROOT=dest_path,
                MEDIA_URL='/site_media/',
                DEBUG=False)

        f = open(os.path.join(source_path, 'a.css'), 'w')
        f.write('div#a { position: absolute; }')
        f.close()

        t = template.Template('{% load css_tags %}{% css_package "p1" %}')
        c = template.Context({})
        compressed = '<link rel="stylesheet" type="text/css" \
href="%s-min.css" />' % (settings.MEDIA_URL + 'p1')
        uncompressed = '<link rel="stylesheet" type="text/css" \
href="%s.css" />' % (settings.MEDIA_URL + 'p1')

        self.failUnlessEqual(t.render(c), compressed)
        self.failIf(os.path.exists(os.path.join(dest_path, "p1.css")))
        self.failIf(os.path.exists(os.path.join(dest_path, "p1-min.css")))

        self.settings_manager.set(DEBUG=True)
        self.failUnlessEqual(t.render(c), uncompressed)
        p1_path = os.path.join(dest_path, 'p1.css')
        self.failUnless(os.path.exists(p1_path))
        f = open(p1_path, 'r')
        self.failUnless(f.read(), 'div#a { position: absolute; }')
        f.close()

        shutil.rmtree(dest_path)
        os.mkdir(dest_path)
        self.settings_manager.set(CSS_BUILDER_COMPRESS=True)
        self.failUnlessEqual(t.render(c), compressed)
        p1_path = os.path.join(dest_path, 'p1-min.css')
        self.failUnless(os.path.exists(p1_path))
        f = open(p1_path, 'r')
        self.failUnlessEqual(f.read(), 'div#a{position:absolute;}')

        shutil.rmtree(dest_path)
        os.mkdir(dest_path)
        self.settings_manager.set(CSS_BUILDER_COMPRESS=False)
        self.failUnlessEqual(t.render(c), uncompressed)
        p1_path = os.path.join(dest_path, 'p1.css')
        self.failUnless(os.path.exists(p1_path))
        f = open(p1_path, 'r')
        self.failUnlessEqual(f.read(), 'div#a { position: absolute; }')

        shutil.rmtree(dest_path)
        os.mkdir(dest_path)
        self.settings_manager.set(CSS_BUILDER_COMPRESS=True)
        request = HttpRequest()
        request.GET["css_compress"] = "0"
        c = template.Context({"request": request})
        self.failUnlessEqual(t.render(c), uncompressed)
        p1_path = os.path.join(dest_path, 'p1.css')
        self.failUnless(os.path.exists(p1_path))
        f = open(p1_path, 'r')
        self.failUnlessEqual(f.read(), 'div#a { position: absolute; }')

        shutil.rmtree(dest_path)
        os.mkdir(dest_path)
        self.settings_manager.set(CSS_BUILDER_COMPRESS=False)
        request.GET["css_compress"] = "1"
        c = template.Context({"request": request})
        self.failUnlessEqual(t.render(c), compressed)
        p1_path = os.path.join(dest_path, 'p1-min.css')
        self.failUnless(os.path.exists(p1_path))
        f = open(p1_path, 'r')
        self.failUnlessEqual(f.read(), 'div#a{position:absolute;}')

    def test_build_package(self):
        os.mkdir(os.path.join(self.rootTestsDir, "data"))
        os.mkdir(os.path.join(self.rootTestsDir, "source"))
        os.mkdir(os.path.join(self.rootTestsDir, "dest"))

        self.settings_manager.set(
                CSS_BUILDER_PACKAGES={"p1": [], "p2": ["a.css"]},
                MEDIA_ROOT=os.path.join(self.rootTestsDir, "dest"),
                CSS_BUILDER_SOURCE=os.path.join(self.rootTestsDir, "source"))

        # wrong package name
        build_package("wrong package name")
        self.failUnless(check_last_log("wrong package name"))
        self.failUnlessEqual(
                    os.listdir(os.path.join(self.rootTestsDir, "dest")), [])

        # empty package
        build_package("p1")

        f = open(os.path.join(self.rootTestsDir, "source", "a.css"), "w")
        f.write("// require b.css\n")
        f.write("// require c.css")
        f.close()
        f = open(os.path.join(self.rootTestsDir, "source", "b.css"), "w")
        f.write("div#b {}")
        f.close()
        f = open(os.path.join(self.rootTestsDir, "source", "c.css"), "w")
        f.write("div#c {}")
        f.close()
        build_package("p2")
        f = open(os.path.join(settings.MEDIA_ROOT, "p2.css"), "r")
        content = f.read()
        f.close()
        self.failUnlessEqual(content, "div#b {}\ndiv#c {}\n// \
require b.css\n// require c.css")

    def test_create_css_sprite_file(self):
        self.settings_manager.set(
                CSS_BUILDER_SPRITES={'sprite#1': {'orientation': 'horizontal'},
                                'sprite#2': {'orientation': 'horizontal',
                                            'format': 'png'}})

        self.failUnlessEqual(create_css_sprite_file('sprite#1', [], 100, 100),
                            None)
        self.failUnlessRaises(Sprite.DoesNotExist, Sprite.objects.get,
                              name='sprite#1')
        self.image_a = here(['tests_files', 'a.png'])
        self.sprite_image_1 = SpriteImageFile(self.image_a, 40, 60)
        create_css_sprite_file('sprite#2', [self.sprite_image_1], 100, 100)
        sprite_2 = Sprite.objects.get(name='sprite#2')
        image_1 = SpriteImage.objects.get(path=self.image_a,
                                        sprite=sprite_2)
        self.failUnlessEqual(image_1.x, 40)
        self.failUnlessEqual(image_1.y, 60)
        self.failUnlessEqual(image_1.sprite, sprite_2)

        self.sprite_image_1 = SpriteImageFile(self.image_a, 60, 80)
        create_css_sprite_file('sprite#2', [self.sprite_image_1], 100, 100)
        image_1 = SpriteImage.objects.get(path=self.image_a, sprite=sprite_2)
        self.failUnlessEqual(image_1.x, 60)
        self.failUnlessEqual(image_1.y, 80)
