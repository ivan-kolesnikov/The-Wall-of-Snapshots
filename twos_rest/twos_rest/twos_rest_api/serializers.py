from rest_framework import serializers
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Channel, Guard, Bitrate, Error, Snap


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'number_default']


class GuardConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guard
        fields = ['id', 'ip', 'port', 'min_bitrate_kbs', 'sleep_time', 'update_errors_time', 'update_bitrate_time']


class ErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Error
        fields = ['id', 'channel_id', 'occurred_on', 'udp_raises', 'udp_amount', 'cc_raises']


class BitrateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitrate
        fields = ['channel_id', 'updated_on', 'bitrate_kbs']

'''
class BitrateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bitrate
        fields = ['bitrate_time', 'bitrate_kbs']
'''


class BitrateChannelSerializer(serializers.ModelSerializer):
    bitrate = BitrateSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'bitrate']


class DroppedChannelsSerializer(serializers.ModelSerializer):
    last_bitrate = serializers.SerializerMethodField("get_last_bitrate_field")

    def get_last_bitrate_field(self, channel):
        bitrate = Bitrate.objects.filter(channel_id=channel.id).order_by('id')
        last_bitrate = bitrate.last()
        serializer = BitrateSerializer(instance=last_bitrate)
        return serializer.data

    class Meta:
        model = Channel
        fields = ['id', 'name', 'last_bitrate']

