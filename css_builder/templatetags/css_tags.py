
import os
from contextlib import closing

from django import template
from django.conf import settings

from css_builder.utils import (build_css_sprite, add_embedding_images,
                               commonpostfix, build_package)


register = template.Library()


@register.tag
def css_package(parser, token):
    try:
        tag_name, package_name = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)
    return CSSPackageNode(package_name[1:-1])


@register.tag
def inline_css(parser, token):
    try:
        tag_name, file_name = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)
    return InlineCSSNode(file_name[1:-1])


@register.tag
def css_file(parser, token):
    try:
        tag_name, package_name = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)
    return CSSFileNode(package_name[1:-1])


class CSSFileNode(template.Node):
    """
    """
    def __init__(self, url):
        self.url = url
        self.rel_file_path = commonpostfix([url, settings.MEDIA_URL])

    def render(self, context):
        input_abspath = os.path.join(settings.MEDIA_ROOT, self.rel_file_path)
        output_abspath = '%s_output%s' %\
                                    (input_abspath[:-4], input_abspath[-4:])
        if settings.DEBUG == True:
            add_embedding_images(input_abspath, output_abspath)
        new_url = os.path.join(settings.MEDIA_URL, '%s_output%s' %\
                    (self.rel_file_path[:-4], self.rel_file_path[-4:]))
        return '<link rel="stylesheet" type="text/css" href="%s" />' % new_url


class InlineCSSNode(template.Node):

    def __init__(self, path):
        self.path = path

    def render(self, context):
        with closing(open(os.path.join(settings.CSS_BUILDER_SOURCE,
                                                        self.path))) as script:
            return "<style type='text/css'>%s</style>" % script.read()


class CSSPackageNode(template.Node):

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
