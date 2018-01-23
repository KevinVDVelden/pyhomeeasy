import json
import struct
import socket
import time
#from collections import defaultdict

HEADER = b'\xff\xee\xaf\xae'
SEPARATOR = b'$'

class Homeeasy:
    def __init__( self, host, user, password ):
        self.host = host
        self.user = user
        self.password = password

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
            return False, None

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

ha = Homeeasy( 'homeeasy.lan', 'admin', '1bbd886460827015e5d605ed44252251' )
print( ha.sendMessage( 'query', 'allinfor', 2 ) )

ha = Homeeasy( 'homeeasy.lan', 'admin', '96e79218965eb72c92a549dd5a330112' )
print( ha.sendMessage( 'query', 'allinfor', 2 ) )

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
