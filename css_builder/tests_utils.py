#
# Source: http://www.djangosnippets.org/snippets/1011/
#
from django.conf import settings, LazySettings
from django.core.management import call_command
from django.db.models import loading
from django.test import TestCase

from css_builder.utils import LOG_FILENAME

NO_SETTING = ('!', None)

class TestSettingsManager(object):
    """
    A class which can modify some Django settings temporarily for a
    test and then revert them to their original values later.

    Automatically handles resyncing the DB if INSTALLED_APPS is
    modified.

    """
    def __init__(self):
        self._original_settings = {}

    def remove(self, list):
        for k in list:
            if hasattr(settings, k):
                self._original_settings.setdefault(k,  getattr(settings, k))
            try:
                delattr(settings, k)
            except AttributeError:
                delattr(settings._wrapped, k)

    def set(self, **kwargs):
        for k,v in kwargs.iteritems():
            self._original_settings.setdefault(k, getattr(settings, k,
                                                          NO_SETTING))
            setattr(settings, k, v)
        if 'INSTALLED_APPS' in kwargs:
            self.syncdb()

    def syncdb(self):
        loading.cache.loaded = False
        call_command('syncdb', verbosity=0)

    def revert(self):
        for k,v in self._original_settings.iteritems():
            if v == NO_SETTING:
                try:
                    delattr(settings, k)
                except AttributeError: 
                    delattr(settings._wrapped, k)
            else:
                setattr(settings, k, v)
        if 'INSTALLED_APPS' in self._original_settings:
            self.syncdb()
        self._original_settings = {}


class SettingsTestCase(TestCase):
    """
    A subclass of the Django TestCase with a settings_manager
    attribute which is an instance of TestSettingsManager.

    Comes with a tearDown() method that calls
    self.settings_manager.revert().

    """
    def __init__(self, *args, **kwargs):
        super(SettingsTestCase, self).__init__(*args, **kwargs)
        self.settings_manager = TestSettingsManager()

    def tearDown(self):
        self.settings_manager.revert()

def check_last_log(msg):
    """
    Check if last message in logging file is msg
    
    Parameters:
        msg <str>
        
    Return:
        bool
    """
    f = open(LOG_FILENAME, "r")
    last_line = f.readlines()[-1]
    f.close()
    if last_line.find(msg) == -1:
        return False
    else:
        return True