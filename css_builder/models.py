
from django.db import models


class CSSSprite(models.Model):
    """
    """
    name = models.CharField(max_length=100, primary_key=True)
    orientation = models.CharField(max_length=100, default="default")

    def __unicode__(self):
        return "%s" % self.name


class CSSSpriteImage(models.Model):
    """
    """
    sprite = models.ForeignKey(CSSSprite, related_name="images")
    path = models.CharField(max_length=200, primary_key=True)
    x = models.IntegerField()
    y = models.IntegerField()

    def __unicode__(self):
        return "%s %d %d" % (self.path, self.x, self.y,)

