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
        serializer = EventsSerialiser(events, many=True)
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


class ChannelDropsList(APIView):
    def get(self, request):
        # get all channels
        channels = Channel.objects.all()
        # create an empty list for dropped channels
        dropped_channels_lst = []
        for channel in channels:
            # get bitrate object for current channel
            bitrate_obj = Bitrate.objects.filter(channel_id=channel.id).order_by('id')
            # get last bitrate for current channel
            last_bitrate_by_id = bitrate_obj.last()
            # if last bitrate too low
            if last_bitrate_by_id.bitrate_kbs < 500:
                # add affected channel in the channels drop list
                dropped_channels_lst.append(channel.id)
        # get dropped channels
        dropped_channels = Channel.objects.filter(id__in=dropped_channels_lst)
        serializer = DroppedChannelsSerializer(dropped_channels, many=True)
        return Response(serializer.data)

    def put(self):
        pass


class ChannelEventList(APIView):
    def get(self, request):
        # choose appropriate complex event
        show_cc = 1
        show_udp = 1
        show_updown = 1
        # get parameters from request query
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

        # duration parameters scanner
        # default duration is 1 month
        events_duration_sec_default = 2592000
        try:
            events_duration_sec = int(req_params['duration'])
        except:
            events_duration_sec = events_duration_sec_default
        context = {"duration": events_duration_sec}

        # gel all channels
        channels = Channel.objects.all()
        # choose necessery serializser
        if show_cc and not show_udp and not show_updown:
            serializer = CcEventChannelSerializer(channels, many=True, context=context)
        elif not show_cc and show_udp and not show_updown:
            serializer = UdpEventChannelSerializer(channels, many=True, context=context)
        elif not show_cc and not show_udp and show_updown:
            serializer = UpDownEventChannelSerializer(channels, many=True, context=context)
        elif show_cc and show_udp and not show_updown:
            serializer = CcUdpEventChannelSerializer(channels, many=True, context=context)
        elif show_cc and not show_udp and show_updown:
            serializer = CcUpDownEventChannelSerializer(channels, many=True, context=context)
        elif not show_cc and show_udp and show_updown:
            serializer = UdpUpDownEventChannelSerializer(channels, many=True, context=context)
        elif show_cc and show_udp and show_updown:
            serializer = CcUdpUpDownEventChannelSerializer(channels, many=True, context=context)
        else:
            return Response({'status': 'error',
                             'description': 'check filter, no events to show',
                             'usage': '?show_cc=1&show_udp=1&show_updown=1'})
        print(serializer.data)

        return Response(serializer.data)

    def post(self):
        pass


class ChannelEventDetail(APIView):
    def get_object(self, pk):
        try:
            return Channel.objects.get(pk=pk)
        except Channel.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
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
        # duration parameters scanner
        # default duration is 1 month
        events_duration_sec_default = 2592000
        try:
            events_duration_sec = int(req_params['duration'])
        except:
            events_duration_sec = events_duration_sec_default
        context = {"duration": events_duration_sec}

        # get requested channel
        channel = self.get_object(pk)
        # choose necessary serializser
        if show_cc and not show_udp and not show_updown:
            serializer = CcEventChannelSerializer(channel, context=context)
        elif not show_cc and show_udp and not show_updown:
            serializer = UdpEventChannelSerializer(channel, context=context)
        elif not show_cc and not show_udp and show_updown:
            serializer = UpDownEventChannelSerializer(channel, context=context)
        elif show_cc and show_udp and not show_updown:
            serializer = CcUdpEventChannelSerializer(channel, context=context)
        elif show_cc and not show_udp and show_updown:
            serializer = CcUpDownEventChannelSerializer(channel, context=context)
        elif not show_cc and show_udp and show_updown:
            serializer = UdpUpDownEventChannelSerializer(channel, context=context)
        elif show_cc and show_udp and show_updown:
            serializer = CcUdpUpDownEventChannelSerializer(channel, context=context)
        else:
            return Response({'status': 'error',
                             'description': 'check filter, no events to show',
                             'usage': '?show_cc=1&show_udp=1&show_updown=1'})
        return Response(serializer.data)

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






