import json
import struct
import socket
import time
#from collections import defaultdict

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

    def __str__( self ):
        return '<Room  %d:%s>' % ( self.id, self.name )

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

    def __str__( self ):
        return '<Switch %d:%s from room %s>' % ( self.id, self.name, self.room.name )

class Homeeasy:
    def __init__( self, host, user, password ):
        self.host = host
        self.user = user
        self.password = password

        self.rawData = None
        self.rawDataRecieved = 0
        self.switchObjects = {}
        self.roomObjects = {}

    def encode( self, *args ):
        message = self.user.encode( 'ascii' ) + SEPARATOR + self.password.encode( 'ascii' ) + SEPARATOR + SEPARATOR.join( [ str( n ).encode( 'ascii' ) for n in args ] )
        return HEADER + struct.pack( '!I', len( message ) ) + message

    def decode( self, message ):
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
            return self.switch( name, False )
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
            print( 'Rebuilding' )
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

#data = tuple( open( 'homeeasy.dump', 'rb' ) )
#
#PREAMBLE = '---------------- Read from: '
#
#parsedData = []
#
#source = None
#packet = bytes()
#for line in data[1:]:
#    strLine = ''
#    try:
#        strLine = line.decode( 'ascii' )
#    except:
#        pass
#
#    if strLine.startswith( PREAMBLE ):
#        if source is not None:
#            parsedData.append( ( source, packet.hex() ) )
#
#        source = strLine[ len( PREAMBLE ): ]
#        source = source[ : source.find( ' ---------' ) ]
#        packet = bytes()
#    else:
#        packet = packet + line
#
#
#json.dump( parsedData, open( 'homeeasy.json', 'w' ) )


allData = json.load( open( 'homeeasy.json', 'r') )
allData = tuple( ( a[:a.find(':')], bytes.fromhex( b )[:-1] ) for a, b  in allData )

#start = {}
#for source, data in allData:
#    if source not in start:
#        start[source] = data[:]
#        continue
#
#    minLen = min( len( start[source] ), len( data ) )
#    for n in range( minLen ):
#        if start[source][ n ] == data[ n ]:
#            minLen = n
#        else:
#            break
#
#    start[source] = start[source][ : minLen + 1 ]
#
#remains = defaultdict( lambda: [] )
#for source, data in allData:
#    remains[source].append( data[ len(start[source]): ] )

ha = Homeeasy( 'homeeasy.lan', 'admin', '96e79218965eb72c92a549dd5a330112' )
print( ha.room( 'Livingroom' ) )
for switch in ha.switches:
    print( switch )
#for room in ha.rawRooms.values():
#    print( room )
#print()
#for switch in ha.rawSwitches:
#    print( switch[0], ha.rawRooms[ switch[1] ] )

#json.dump( ha.status, open( 'homeeasy.rooms.json', 'w' ), indent=4, sort_keys=True )

#for source, message in allData:
#    if source != 'homeeasy.lan':
#        print( source )
#        print( message[8:] )
#        print()
#        continue
#
#    print( source )
#    ha.decode( message )
#    print()
