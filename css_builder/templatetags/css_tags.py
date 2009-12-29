
import os
from contextlib import closing

from django import template
from django.conf import settings

from css_builder.utils import build_sprite

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


class InlineCSSNode(template.Node):

    def __init__(self, path):
        self.path = path

    def render(self, context):
        with closing(open(os.path.join(settings.CSS_BUILDER_SOURCE,
                                                        self.path))) as script:
            return "<style type='text/css'>%s</style>" % script.read()


class JSPackageNode(template.Node):

    def __init__(self, package_name):
        self.package_name = str(package_name)

    def render(self, context):
        compressed_package = "<link rel='stylesheet' type='text/css' href='" +\
                settings.MEDIA_URL + self.package_name + "-min.css' />"

        if settings.DEBUG == False:
            build_sprite(self.package_name, compress=True)
            return compressed_package

        uncompressed_package = \
                            "<link rel='stylesheet' type='text/css' href='" +\
                            settings.MEDIA_URL + self.package_name + ".css' />"

        if "request" in context:
            compress = context["request"].GET.get("css_compress", "False")
            if compress == "True":
                build_sprite(self.package_name, compress=True)
                return compressed_package
            elif compress == "False":
                build_sprite(self.package_name)
                return uncompressed_package

        if hasattr(settings, "CSS_BUILDER_COMPRESS"):
            if getattr(settings, "CSS_BUILDER_COMPRESS"):
                build_sprite(self.package_name, compress=True)
                return compressed_package

        build_sprite(self.package_name)
        return uncompressed_package
