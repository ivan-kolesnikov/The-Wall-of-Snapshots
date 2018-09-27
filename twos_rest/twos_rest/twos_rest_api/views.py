from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from orca.settings import speakMultiCaseStringsAsWords
from rest_framework import viewsets
#from twos_rest.twos_rest.twos_rest_api.models import

from rest_framework.views import APIView
from .models import Channel
from .serializers import ChannelSerializer, StatisticSerializer
from rest_framework.response import Response

from django.http import Http404


class ChannelsList(APIView):
    def get(self, request):
        channels = Channel.objects.all()
        serializer = ChannelSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass


class ChannelDetail(APIView):
    """
    Retrieve, update or delete a user instance.
    """
    def get_object(self, pk):
        try:
            return Channel.objects.get(pk=pk)
        except Channel.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        channel = self.get_object(pk)
        channel = ChannelSerializer(channel)
        return Response(channel.data)

    def put(self, request, pk, format=None):
        pass

    def delete(self, request, pk, format=None):
        pass


class StatisticList(APIView):
    def get(self, request):
        get_data = request.query_params
        print(get_data)
        #channels = Channel.objects.all()
        channels = Channel.objects.filter(name=get_data['name'])

        serializer = StatisticSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass







