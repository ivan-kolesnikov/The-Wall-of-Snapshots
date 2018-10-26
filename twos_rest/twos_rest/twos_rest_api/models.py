from django.db import models


class Channel(models.Model):
    id = models.PositiveIntegerField(primary_key=True)
    name = models.CharField(max_length=400)
    multicast = models.CharField(max_length=100)
    number_default = models.PositiveIntegerField(null=True)

    def __str__(self):
        return self.name


class Guard(models.Model):
    id = models.AutoField(primary_key=True)
    ip = models.CharField(max_length=100)
    port = models.PositiveIntegerField(null=True)
    min_bitrate_kbs = models.PositiveIntegerField(null=True)
    sleep_time = models.PositiveIntegerField(null=True)
    update_errors_time = models.PositiveIntegerField(null=True)
    update_bitrate_time = models.PositiveIntegerField(null=True)


class Bitrate(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True, related_name='bitrate')
    updated_on = models.DateTimeField(null=True)
    bitrate_kbs = models.PositiveIntegerField(null=True)


class Error(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True, related_name='error')
    occurred_on = models.DateTimeField(null=True)
    udp_raises = models.PositiveIntegerField(null=True)
    udp_amount = models.PositiveIntegerField(null=True)
    cc_raises = models.PositiveIntegerField(null=True)


class Snap(models.Model):
    id = models.AutoField(primary_key=True)
    channel = models.ForeignKey(Channel, on_delete=models.DO_NOTHING, null=True)
    updated_on = models.DateTimeField(null=True)
    snap_location = models.CharField(max_length=500)
