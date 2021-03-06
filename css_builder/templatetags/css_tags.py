
import os
from contextlib import closing

from django import template
from django.conf import settings

from css_builder.utils import (build_css_sprite, add_embedding_images,
                               cut_path, build_package, log, add_css_sprites)


register = template.Library()


@register.tag
def css_package(parser, token):
    try:
        tag_name, package_name = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)
    return CssPackageNode(package_name[1:-1])


@register.tag
def css_file(parser, token):
    try:
        tag_name, package_name = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)
    return CssFileNode(package_name[1:-1])


class CssPackageNode(template.Node):

    def __init__(self, package_name):
        self.package_name = str(package_name)

    def render(self, context):
        compressed_package = '<link rel="stylesheet" type="text/css" \
href="%s-min.css" />' % (settings.MEDIA_URL + self.package_name)

        # If settings.DEBUG is False then build_package won't be run
        if settings.DEBUG == False:
            return compressed_package

        uncompressed_package = '<link rel="stylesheet" type="text/css" \
href="%s.css" />' % (settings.MEDIA_URL + self.package_name)

        if "request" in context:
            compress = context["request"].GET.get("css_compress", "0")
            if compress == "1":
                build_package(self.package_name, compress=True)
                return compressed_package
            elif compress == "0":
                build_package(self.package_name)
                return uncompressed_package

        if hasattr(settings, "CSS_BUILDER_COMPRESS"):
            if getattr(settings, "CSS_BUILDER_COMPRESS"):
                build_package(self.package_name, compress=True)
                return compressed_package
        build_package(self.package_name)
        return uncompressed_package


class CssFileNode(template.Node):
    """
    """
    def __init__(self, path):
        self.path = path
        self.dir_path = os.path.dirname(self.path)

    def render(self, context):
        input_abspath = os.path.join(settings.CSS_BUILDER_SOURCE,
                                     self.path)
        if not os.path.exists(input_abspath):
            msg = '%s (%s) does not exists.' % (self.path, input_abspath)
            log('css_file', msg)
            return '<!--\n%s\n-->' % msg
        if self.dir_path != '':
            os.makedirs(os.path.join(settings.MEDIA_ROOT, self.dir_path))

        output_abspath = os.path.join(settings.MEDIA_ROOT, self.path)

        if settings.DEBUG == True:
            add_embedding_images(input_abspath, output_abspath)
            add_css_sprites(output_abspath)
        url = os.path.join(settings.MEDIA_URL, self.path)
        return '<link rel="stylesheet" type="text/css" href="%s" />' % url
