from rest_framework import serializers
from .models import Channel, Event, CC_error, UDP_error, Updown_error


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default']


class CcErrorSerialiser(serializers.ModelSerializer):
    class Meta:
        model = CC_error
        fields = ['amount']


class UdpErrorSerialiser(serializers.ModelSerializer):
    class Meta:
        model = UDP_error
        fields = ['raise_counter', 'amount']


class UpDownErrorSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Updown_error
        fields = ['state', 'bitrate_kbs']


class EventSerializer(serializers.ModelSerializer):
    CC_errors = CcErrorSerialiser(many=True)
    UDP_errors = UdpErrorSerialiser(many=True)
    Updown_errors = UpDownErrorSerialiser(many=True)

    class Meta:
        model = Event
        fields = ['id', 'event_time', 'CC_errors', 'UDP_errors', 'Updown_errors']


class ChannelEventSerializer(serializers.ModelSerializer):
    event = EventSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default', 'event']


'''
class ErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Error
        fields = '__all__'



class StatisticSerializer(serializers.ModelSerializer):
    errors = ErrorSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'errors']
'''