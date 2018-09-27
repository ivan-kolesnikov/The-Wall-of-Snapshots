from django.db import models

# Create your models here.
from django.db import models


class Channel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150)
    multicast = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Error(models.Model):
    id = models.AutoField(primary_key=True)
    error_time = models.DateTimeField(null=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, related_name='errors', null=True)
    #channel_id = models.PositiveIntegerField(null=True)
    cc_error_raise_counter = models.PositiveIntegerField()
    udp_error_raise_counter = models.PositiveIntegerField()
    udp_lost_packages_counter = models.PositiveIntegerField()

    class Meta:
        unique_together = ('channel', 'id')
        ordering = ['id']

    def __unicode__(self):
        return '%d: %s' % (self.cc_error_raise_counter, str(self.udp_error_raise_counter))


class Bitrate(models.Model):
    bitrate_time = models.DateTimeField(null=True)
    channel_id = models.PositiveIntegerField()
    bitrate_kbs = models.PositiveIntegerField()


class Snap(models.Model):
    channel_id = models.PositiveIntegerField()
    snap_location = models.CharField(max_length=500)
    last_update_time = models.DateTimeField(null=True)
