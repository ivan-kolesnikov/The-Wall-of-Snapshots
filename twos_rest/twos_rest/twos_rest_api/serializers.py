from rest_framework import serializers
from .models import Channel, Event, CC_error, UDP_error, Updown_error
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework.validators import UniqueTogetherValidator


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default']


# Simple Events
class CcErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CC_error
        fields = ['amount']


class UdpErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UDP_error
        fields = ['raise_counter', 'amount']


class UpDownErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Updown_error
        fields = ['state', 'bitrate_kbs']


# Complex Events
class CcEventSerializer(serializers.ModelSerializer):
    CC_errors = CcErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'CC_errors']


class UdpEventSerializer(serializers.ModelSerializer):
    UDP_errors = UdpErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'UDP_errors']


class UpDownEventSerializer(serializers.ModelSerializer):
    Updown_errors = UpDownErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'Updown_errors']


class CcUdpEventSerializer(serializers.ModelSerializer):
    CC_errors = CcErrorSerializer(many=True)
    UDP_errors = UdpErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'CC_errors', 'UDP_errors']


class CcUpDownEventSerializer(serializers.ModelSerializer):
    CC_errors = CcErrorSerializer(many=True)
    Updown_errors = UpDownErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'CC_errors', 'Updown_errors']


class UdpUpDownEventSerializer(serializers.ModelSerializer):
    UDP_errors = UdpErrorSerializer(many=True)
    Updown_errors = UpDownErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'UDP_errors', 'Updown_errors']


class CcUdpUpDownEventSerializer(serializers.ModelSerializer):
    CC_errors = CcErrorSerializer(many=True)
    UDP_errors = UdpErrorSerializer(many=True)
    Updown_errors = UpDownErrorSerializer(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'CC_errors', 'UDP_errors', 'Updown_errors']


# Complex Events Channels
class CcEventChannelSerializer(serializers.ModelSerializer):
    events = CcEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UdpEventChannelSerializer(serializers.ModelSerializer):
    events = UdpEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UpDownEventChannelSerializer(serializers.ModelSerializer):
    events = UpDownEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUdpEventChannelSerializer(serializers.ModelSerializer):
    events = CcUdpEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUpDownEventChannelSerializer(serializers.ModelSerializer):
    events = CcUpDownEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UdpUpDownEventChannelSerializer(serializers.ModelSerializer):
    events = UdpUpDownEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUdpUpDownEventChannelSerializer(serializers.ModelSerializer):
    events = CcUdpUpDownEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']

'''
class ChannelEventSerializer(serializers.ModelSerializer):
    events = CcUdpUpDownEventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']
'''
