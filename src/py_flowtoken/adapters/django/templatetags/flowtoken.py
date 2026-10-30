from django import template
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from ....assets import asset_path
from ....rendering import AnimatedImage, AnimatedMarkdown, AnimatedText

register = template.Library()


@register.simple_tag
def flowtoken_asset_url(filename):
    asset_path(filename)
    mode = getattr(settings, "FLOWTOKEN_ASSET_MODE", "static")
    if mode == "static":
        return static("py_flowtoken/" + filename)
    if mode == "route":
        return reverse("py_flowtoken:asset", kwargs={"filename": filename})
    raise ValueError("FLOWTOKEN_ASSET_MODE must be static or route")


@register.simple_tag
def flowtoken_assets():
    return format_html(
        '<link rel="stylesheet" href="{}"><script type="module" src="{}"></script>',
        flowtoken_asset_url("flowtoken.css"),
        flowtoken_asset_url("flowtoken.js"),
    )


@register.simple_tag
def flowtoken_text(content="", **options):
    return mark_safe(AnimatedText(content, **options).render())


@register.simple_tag
def flowtoken_markdown(content="", **options):
    return mark_safe(AnimatedMarkdown(content, **options).render())


@register.simple_tag
def flowtoken_image(src, alt="", **options):
    return mark_safe(AnimatedImage(src, alt, **options).render())
