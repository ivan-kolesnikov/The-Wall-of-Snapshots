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
from rest_framework import status


from django.http import Http404


import mysql.connector
from mysql.connector import errorcode


from pprint import pprint


class ChannelsList(APIView):
    def get(self, request):
        channels = Channel.objects.all().order_by('number_default')
        serializer = ChannelSerializer(channels, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = ChannelSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        channel = self.get_object(pk)
        serializer = ChannelSerializer(channel, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        channel = self.get_object(pk)
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChannelsUpdate(APIView):
    def get(self, request):
        print("NEW CYCLE!!!!!")
        # connect to MySQL
        try:
            db = mysql.connector.connect(user='root_ivan',
                                         password='qwerty',
                                         host='127.0.0.1',
                                         database='stalker_db',
                                         charset='cp1251',
                                         use_unicode=True)
            #db.set_charset_collation('utf8', 'default_collation')
            cursor_db = db.cursor(dictionary=True)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                return Response({'detail': 'Username or password incorrect.'})
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                return Response({'detail': 'Database does not exist.'})
            else:
                return Response({'detail': str(err)})
        except Exception as err:
            return Response({'detail': 'Failed to connect to the Data Base '+str(err)})

        try:
            cursor_db.execute("SELECT itv.id, name, mc_cmd as multicast, number as number_default FROM stalker_db.itv "
                              "LEFT JOIN stalker_db.service_in_package "
                              "ON stalker_db.service_in_package.service_id=itv.id "
                              "WHERE (package_id IN (6,8,9,10,11,12,13,14,17,19,20,27,28,30) and status = 1) "
                              "GROUP BY id, name, cmd ORDER BY number;")
            channels_production = cursor_db.fetchall()
        except Exception as err:
            return Response({'detail': 'Can not select jobs from DB ' + str(err)})
        # if channels list is empty
        if len(channels_production) < 1:
            return Response({'detail': 'Channels list from MySQL DB is empty.'})
        # fixing legacy dirty hack with <div> in naming
        for i, _ in enumerate(channels_production):
            if "div class" in channels_production[i]['name']:
                start_tag_pos = channels_production[i]['name'].find("<")
                channels_production[i]['name'] = channels_production[i]['name'][:start_tag_pos] + ' Promo'
        # get all channels objects
        channels_api = Channel.objects.all()
        # try to delete unused channels and update channels fields in channels_api
        for channel_api in channels_api:
            found = 0
            for channel_production in channels_production:
                # try to find channel from API in production DB
                if channel_api.id == channel_production['id']:
                    found = 1
                    # check fields and update then if it's necessary
                    '''
                    if channel_api.name != channel_production['name']:
                        channel_production_raw = channel_production['name']
                        print("!!!!!!!!!!!!!!!!!!!!")
                        pprint(channel_production_raw)
                        print("!!!!!!!!!!!!!!!!!!!!")
                        channel_api.name = channel_production_raw.encode('utf8')
                        channel_api.save()
                        print("UPDATE: NAME")
                    if channel_api.multicast != channel_production['multicast']:
                        channel_api.multicast = channel_production['multicast']
                        channel_api.save()
                        print("UPDATE: MULTICAST")
                    if channel_api.number_default != channel_production['number_default']:
                        channel_api.number_default = channel_production['number_default']
                        channel_api.save()
                        print("UPDATE: NUMBER_DEFAULT")
                    '''
                    #!!!! obj.save()
                    # go to the next channel in case of success
                    break
            # if channel_id has not found - delete it from channels_api
            if not found:
                print("channel_id="+str(channel_api.id))
                print("DELETE!!!!")
                channel_api.delete()
        # trying to find and add new channels from middleware
        for channel_production in channels_production:
            found = 0
            # !!!! maybe is nesseccary to get all channels from API again
            for channel_api in channels_api:
                if channel_production['id'] == channel_api.id:
                    found = 1
                    break
            # if channel has not found
            if not found:
                # add this channels in api
                print("ADD NEW CHANNEL")
                Channel.objects.create(id=channel_production['id'], name=channel_production['name'],
                                       multicast=channel_production['multicast'],
                                       number_default=channel_production['number_default'])
        #return Response(channels_api)
        return Response("DONE!")

class EventsList(APIView):
    def get(self, request):
        # get events in desc order
        events = Event.objects.all().order_by('-id')
        serializer = EventsSerialiser(events, many=True)
        return Response(serializer.data)

    def post(self):
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






