from django.db import models

# Create your models here.
from django.db import models
import datetime
import dateutil



class Channel(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=400)
    multicast = models.CharField(max_length=100)
    number_default = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.name

class Bitrate(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True, related_name='bitrate')
    bitrate_time = models.DateTimeField(null=True)
    bitrate_kbs = models.PositiveIntegerField(null=True)


class Snap(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True)
    snap_location = models.CharField(max_length=500)
    last_update_time = models.DateTimeField(null=True)


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True, related_name='events')
    event_time = models.DateTimeField(null=True)

    '''def __str__(self):
        return self.name

    def __unicode__(self):
        return '%d: %s' % (self.id, str(self.id))'''


class CC_error(models.Model):
    id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, related_name='CC_errors')
    amount = models.PositiveIntegerField(null=True)


class UDP_error(models.Model):
    id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, related_name='UDP_errors')
    raise_counter = models.PositiveIntegerField()
    amount = models.PositiveIntegerField()


class Updown_error(models.Model):
    id = models.AutoField(primary_key=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, related_name='Updown_errors')
    state = models.IntegerField()
    bitrate_kbs = models.PositiveIntegerField()


'''
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
'''
