import paho.mqtt.client as mqtt
import homeeasy

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
        print( 'Connected.' )
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


# The callback for when a PUBLISH message is received from the server.


client = mqtt.Client()
persistence = MqttPersistence( 'ha/switch/homeeasy', client )
ha = homeeasy.HomeEasy( 'homeeasy.lan', 'admin', '96e79218965eb72c92a549dd5a330112', persistence )
persistence.set_homeeasy( ha )

client.connect('localhost', 1883, 60)

client.loop_forever()
