"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
import os
import shutil

from django.test import TestCase

from css_builder.utils import background2b64, here
from css_builder.tests_utils import SettingsTestCase

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

    def test_background2b64(self):
        self.settings_manager.set(MEDIA_ROOT=here(["tests_data"]))
        f = open(os.path.join(self.rootTestsDir, "a.png"), "w")
        f.write("abcdef")
        f.close()
        css_file = os.path.join(self.rootTestsDir, "t.css")
        f = open(css_file, "w")
        f.write("background-image: url(a.png); /* 2b64 */")
        f.close()
        background2b64(css_file)
        f = open(css_file, "r")
        content = f.read()
        f.close()
        self.failUnlessEqual(content, "background-image: url(%s);" %\
                        ("data:image/png;base64," + "abcdef".encode("base64")))

        f = open(css_file, "w")
        f.write("background: #808080 url(a.png) no-repeat 0px 0px; /* 2b64 */")
        f.close()
        background2b64(css_file)
        f = open(css_file, "r")
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
                        "background: #808080 url(%s) no-repeat 0px 0px;" %\
                        ("data:image/png;base64," + "abcdef".encode("base64")))

        f = open(css_file, "w")
        f.write("background: red url(a.png) no-repeat top left; /* 2b64 */")
        f.close()
        background2b64(css_file)
        f = open(css_file, "r")
        content = f.read()
        f.close()
        self.failUnlessEqual(content,
                        "background: red url(%s) no-repeat top left;" %\
                        ("data:image/png;base64," + "abcdef".encode("base64")))

