from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from orca.settings import speakMultiCaseStringsAsWords
from rest_framework import viewsets
#from twos_rest.twos_rest.twos_rest_api.models import

from rest_framework.views import APIView
from .models import Channel, Event
from .serializers import *
from rest_framework.response import Response


from django.http import Http404


class ChannelsList(APIView):
    def get(self, request):
        channels = Channel.objects.all()
        serializer = ChannelSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass
    
    
class EventsList(APIView):
    def get(self, request):
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
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


class ChannelEventList(APIView):
    def get(self, request):
        # choose appropriate complex event
        show_cc = 1
        show_udp = 1
        show_updown = 1
        # get parameters from request querry
        req_params = request.query_params
        # check show_cc flag
        try:
            if req_params['show_cc'] != "1":
                show_cc = 0
        except MultiValueDictKeyError:
            show_cc = 0
        # check show_udp flag
        try:
            if req_params['show_udp'] != "1":
                show_udp = 0
        except MultiValueDictKeyError:
            show_udp = 0
        # check show_updown flag
        try:
            if req_params['show_updown'] != "1":
                show_updown = 0
        except MultiValueDictKeyError:
            show_updown = 0

        # gel all channels
        channels = Channel.objects.all()
        print(show_cc, show_udp, show_updown)
        # choose necessery serializser
        if show_cc and not show_udp and not show_updown:
            print("1")
            serializer = CcEventChannelSerializer(channels, many=True)
        elif not show_cc and show_udp and not show_updown:
            print("2")
            serializer = UdpEventChannelSerializer(channels, many=True)
        elif not show_cc and not show_udp and show_updown:
            print("3")
            serializer = UpDownEventChannelSerializer(channels, many=True)
        elif show_cc and show_udp and not show_updown:
            print("4")
            serializer = CcUdpEventChannelSerializer(channels, many=True)
        elif show_cc and not show_udp and show_updown:
            print("5")
            serializer = CcUpDownEventChannelSerializer(channels, many=True)
        elif not show_cc and show_udp and show_updown:
            print("6")
            serializer = UdpUpDownEventChannelSerializer(channels, many=True)
        else:
            print("7")
            serializer = CcUdpUpDownEventChannelSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass


''' DEFAULT
class ChannelEventList(APIView):
    def get(self, request):
        channels = Channel.objects.all()
        serializer = ChannelEventSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass
'''


class ChannelEventDetail(APIView):
    def get_object(self, pk):
        try:
            return Channel.objects.get(pk=pk)
        except Channel.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        channel = self.get_object(pk)
        channel = ChannelEventSerializer(channel)
        return Response(channel.data)

    def put(self, request, pk, format=None):
        pass

    def delete(self, request, pk, format=None):
        pass

'''
class StatisticList(APIView):
    def get(self, request):
        get_data = request.query_params
        print(get_data)
        #channels = Channel.objects.all()
        #channels = Channel.objects.filter(name=get_data['name'])
        channels = Channel.objects.all()

        serializer = StatisticSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self):
        pass
'''






