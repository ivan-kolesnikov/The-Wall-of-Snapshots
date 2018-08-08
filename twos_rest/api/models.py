from django.db import models


class Channel(models.Model):
    name = models.CharField(max_length=150)
    multicast = models.CharField(max_length=100)


class Error(models.Model):
    cc_error_raise_counter = models.PositiveIntegerField()
    udp_error_raise_counter = models.PositiveIntegerField()
    udp_lost_packages_counter = models.PositiveIntegerField()

