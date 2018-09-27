from rest_framework import serializers
from .models import Channel, Error


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast']


class ErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Error
        fields = '__all__'


class StatisticSerializer(serializers.ModelSerializer):
    errors = ErrorSerializer(many=True)

    class Meta:
        model = Channel
        fields = ['id', 'name', 'multicast', 'errors']
