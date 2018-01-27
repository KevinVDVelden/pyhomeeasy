import json
import struct
import socket
import time
from persistence import JsonPersistence

HEADER = b'\xff\xee\xaf\xae'
SEPARATOR = b'$'

class Room:
    def __init__( self, homeeasy, data ):
        self.homeeasy = homeeasy
        self.data = data

    @property
    def name( self ):
        return self.data['roomname']
    @property
    def id( self ):
        return self.data['roomid']
    @property
    def switches( self ):
        for switch in self.data['switchdev']:
            yield self.homeeasy.switch( switch['devid'] )

    def turn_on( self ):
        self.set_state( True )
    def turn_off( self ):
        self.set_state( False )

    def set_state( self, new_state ):
        for switch in self.switches:
            switch.set_state( new_state )

    def __str__( self ):
        return '<Room %d:"%s">' % ( self.id, self.name )

class Switch:
    def __init__( self, homeeasy, room, data ):
        self.homeeasy = homeeasy
        self.data = data
        self.room = room

    @property
    def name( self ):
        return self.data['devname']
    @property
    def id( self ):
        return self.data['devid']

    @property
    def is_on( self ):
        return self.homeeasy.get_state( 'switch', int( self.data['devid'] ), False )

    def turn_on( self ):
        self.set_state( True )
    def turn_off( self ):
        self.set_state( False )

    def set_state( self, new_state ):
        if new_state == 'on':
            new_state = True
        elif new_state == 'off':
            new_state = False

        return self.homeeasy.set_state( 'switch', str( self.data['devid'] ), new_state, False )

    def __str__( self ):
        return '<Switch %d:"%s" from room "%s">' % ( self.id, self.name, self.room.name )

class HomeEasy:
    def __init__( self, host, user, password, persistence = None ):
        self.host = host
        self.user = user
        self.password = password

        self.rawData = None
        self.rawDataRecieved = 0
        self.switchObjects = {}
        self.roomObjects = {}

        if persistence is None:
            persistence = 'homeeasy-persistence.json'

        if type( persistence ) is str:
            self.persistence = JsonPersistence( persistence )
        else:
            self.persistence = persistence

    def encode( self, *args ):
        message = self.user.encode( 'ascii' ) + SEPARATOR + self.password.encode( 'ascii' ) + SEPARATOR + SEPARATOR.join( [ str( n ).encode( 'ascii' ) for n in args ] )
        return HEADER + struct.pack( '!I', len( message ) ) + message

    def decode( self, message ):
        print( 'Decoding message', message )
        assert( HEADER == message[:4] )
        length = struct.unpack_from( '!I', message, 4 )[0]
        assert( length == ( len( message ) - 8 ) )

        ack = message[ 8: 14 ]
        if ack == b'ack100':
            if length > 6:
                return True, json.loads( message[ 14: ].decode( 'ascii' ) )
            else:
                return True, None
        else:
            return False, ack

    def sendMessage( self, *args ):
        message = self.encode( *args )
        print( 'Sending message:', message )

        _socket = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
        _socket.connect( ( self.host, 58168 ) )
        _socket.send( message )

        retrieved = bytes()
        while True:
            data = _socket.recv( 4096 )
            if data == b'':
                break
            retrieved += data

        return self.decode( retrieved )

    def get_state( self, dev_type, dev_id, default ):
        ret = self.persistence.get( ( dev_type, dev_id ) )
        if ret is None:
            return default

        return ret

    def set_state( self, dev_type, dev_id, new_state, default ):
        if self.get_state( dev_type, dev_id, -1 ) == new_state:
            return True

        is_ok, message = self.sendMessage( 'ctrl', dev_type, dev_id, 'on$' if new_state else 'off$' )
        if is_ok:
            self.persistence.set( ( dev_type, dev_id ), new_state )

            return True
        else:
            return False


    def isDataStale( self ):
        return self.rawData is None or ( time.time() - self.rawDataRecieved ) > 1

    @property
    def status( self ):
        if self.isDataStale():
            correct, data = self.sendMessage( 'query', 'allinfor', '2' )
            if correct:
                self.rawData = data
            else:
                raise Exception( 'Unable to fetch status, ' + data )
            self.rawDataRecieved = time.time()

        return self.rawData

    @property
    def rawRooms( self ):
        return { room['roomid']: room for room in self.status['room'] }

    @property
    def rawSwitches( self ):
        for room in self.rawRooms.values():
            for switch in room['switchdev']:
                yield switch, room['roomid']

    def room( self, name, allow_rebuild = True ):
        if name in self.roomObjects:
            return self.roomObjects[ name ]

        if allow_rebuild:
            self.rebuild()
            return self.room( name, False )
        else:
            return None

    def switch( self, name, allow_rebuild = True ):
        if name in self.switchObjects:
            return self.switchObjects[ name ]

        if allow_rebuild:
            self.rebuild()
            return self.switch( name, False )
        else:
            return None

    def rebuild( self, force = False ):
        if force or self.isDataStale() or len( self.switchObjects ) == 0:
            #First, clear all string keys
            for key in tuple( self.roomObjects.keys() ):
                if type( key ) is str:
                    del self.roomObjects[key]
            for key in tuple( self.switchObjects.keys() ):
                if type( key ) is str:
                    del self.switchObjects[key]

            for room in self.status['room']:
                roomId = room['roomid']
                if roomId in self.roomObjects:
                    roomObject = self.roomObject[roomId]
                else:
                    roomObject = Room( self, room )
                    self.roomObjects[roomId] = roomObject

                self.roomObjects[room['roomname']] = roomObject

                for switch in room['switchdev']:
                    devId = switch['devid']
                    if devId in self.switchObjects:
                        switchObject = self.switchObject[devId]
                    else:
                        switchObject = Switch( self, roomObject, switch )
                        self.switchObjects[devId] = switchObject

                    self.switchObjects[switch['devname']] = switchObject


    @property
    def rooms( self ):
        self.rebuild()
        return tuple( self.roomObjects[n] for n in self.roomObjects if type( n ) is int )

    @property
    def switches( self ):
        self.rebuild()
        return tuple( self.switchObjects[n] for n in self.switchObjects if type( n ) is int )

