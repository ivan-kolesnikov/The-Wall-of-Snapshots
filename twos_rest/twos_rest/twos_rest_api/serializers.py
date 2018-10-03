from rest_framework import serializers
from .models import Channel, Event, CC_error, UDP_error, Updown_error
from django.db.models import Q
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
    events = serializers.SerializerMethodField('get_cc_events')

    def get_cc_events(self, channel):
        filtered_events = Event.objects.filter(CC_errors__isnull=False, channel=channel)
        serializer = CcEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UdpEventChannelSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField('get_udp_events')

    def get_udp_events(self, channel):
        filtered_events = Event.objects.filter(UDP_errors__isnull=False, channel=channel)
        serializer = UdpEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UpDownEventChannelSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField('get_updown_events')

    def get_updown_events(self, channel):
        filtered_events = Event.objects.filter(Updown_errors__isnull=False, channel=channel)
        serializer = UpDownEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUdpEventChannelSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField('get_cc_udp_events')

    def get_cc_udp_events(self, channel):
        exist_cc_error = Q(CC_errors__isnull=False)
        exist_udp_error = Q(UDP_errors__isnull=False)
        # CC or UDP errors should be in the events list to add them in the response
        filtered_events = Event.objects.filter(exist_cc_error or exist_udp_error, channel=channel)
        serializer = CcUdpEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUpDownEventChannelSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField('get_cc_updown_events')

    def get_cc_updown_events(self, channel):
        exist_cc_error = Q(CC_errors__isnull=False)
        exist_updown_event = Q(Updown_errors__isnull=False)
        # CC error or Updown event should be in the events list to add them in the response
        filtered_events = Event.objects.filter(exist_cc_error or exist_updown_event, channel=channel)
        serializer = CcUpDownEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class UdpUpDownEventChannelSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField('get_udp_updown_events')

    def get_udp_updown_events(self, channel):
        exist_udp_error = Q(UDP_errors__isnull=False)
        exist_updown_event = Q(Updown_errors__isnull=False)
        # UDP error or Updown event should be in the events list to add them in the response
        filtered_events = Event.objects.filter(exist_udp_error or exist_updown_event, channel=channel)
        serializer = UdpUpDownEventSerializer(instance=filtered_events, many=True)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'events']


class CcUdpUpDownEventChannelSerializer(serializers.ModelSerializer):
    #events = CcUdpUpDownEventSerializer(many=True)
    events = serializers.SerializerMethodField('get_eventss')

    def get_eventss(self, channel):
        from datetime import datetime, timedelta
        time_from = datetime.now()-timedelta(seconds=60000000)
        time_to = datetime.now()
        print("time_from="+str(time_from)+" time_to="+str(time_to))
        #qs = Event.objects.filter(event_time__gte=datetime.now()-timedelta(seconds=1), channel=channel)
        qs = Event.objects.filter(event_time__range=(time_from, time_to), CC_errors__isnull=False, channel=channel)
        serializer = CcUdpUpDownEventSerializer(instance=qs, many=True)
        return serializer.data


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
