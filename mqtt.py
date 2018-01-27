import paho.mqtt.client as mqtt
import homeeasy
import os

class MqttPersistence:
    def __init__( self, prefix, client ):
        self.client = client
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.prefix = prefix
        if self.prefix[-1] != '/':
            self.prefix += '/'

        self.data = {}

    def set_homeeasy( self, homeeasy ):
        self.homeeasy = homeeasy

    def on_connect( self, client, userdata, flags, rc ):
        assert( client == self.client )
        print( 'Connected and subscribing to "%s".' % ( self.prefix, ) )
        client.subscribe( self.prefix + '#' )

    def on_message( self, client, userdata, msg ):
        print( msg.topic+" "+str(msg.payload) )
        if not msg.topic.startswith( self.prefix ):
            return

        if msg.payload == b'on':
            value = True
        elif msg.payload == b'off':
            value = False
        else:
            value = msg.payload.decode( 'utf8' )
            try:
                value = int( value )
            except:
                try:
                    value = float( value )
                except:
                    pass
        
        topic = msg.topic[ len( self.prefix ): ].split( '/' )
        if len( topic ) == 2:
            if topic[1] == 'set':
                self.homeeasy.set_state( 'switch', topic[0], value, None )
            else:
                print( 'Unknown topic: ' + '/'.join( topic ) )
        elif len( topic ) == 1:
            self.data[ topic[ 0 ] ] = value
        else:
            print( 'Unknown topic: ' + '/'.join( topic ) )



    def get( self, key ):
        key = str( key[-1] )
        if key in self.data:
            return self.data[ key ]

    def set( self, key, value ):
        if value == True:
            value = b'on'
        elif value == False:
            value = b'off'
        elif type( value ) != bytes:
            value = str( value ).encode( 'ascii' )

        key = self.prefix + key[1]
        self.client.publish( key, payload = value, retain = True )


MQTT_BROKER                 = os.getenv( 'MQTT_BROKER',            'localhost' )
MQTT_PREFIX                 = os.getenv( 'MQTT_PREFIX',            'ha/switch/homeeasy' )

HOMEEASY_ADDRESS            = os.getenv( 'HOMEEASY_ADDRESS',       'homeeasy.lan' )
HOMEEASY_USER               = os.getenv( 'HOMEEASY_USER',          'admin' )
HOMEEASY_PASSWORD_HASH      = os.getenv( 'HOMEEASY_PASSWORD_HASH', '96e79218965eb72c92a549dd5a330112' )

client = mqtt.Client()
persistence = MqttPersistence( MQTT_PREFIX, client )
ha = homeeasy.HomeEasy( HOMEEASY_ADDRESS, HOMEEASY_USER, HOMEEASY_PASSWORD_HASH, persistence )
persistence.set_homeeasy( ha )

client.connect( MQTT_BROKER, 1883, 60 )

client.loop_forever()
