import paho.mqtt.client as mqtt
import homeeasy
import os
import time
import json

class MqttPersistence:
    def __init__( self, prefix, client ):
        self.client = client
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.prefix = prefix
        if self.prefix[-1] != '/':
            self.prefix += '/'

        self.data = {}
        self.topic_mapping = {}

    def set_homeeasy( self, homeeasy, discovery_prefix ):
        self.homeeasy = homeeasy

        if discovery_prefix != '' and discovery_prefix[-1] != '/':
                discovery_prefix += '/'

        self.discovery_prefix = discovery_prefix

    def on_connect( self, client, userdata, flags, rc ):
        assert( client == self.client )
        print( 'Connected and subscribing to "%s".' % ( self.prefix, ) )
        client.subscribe( self.prefix + '#' )
        print( 'Done' )

        if self.discovery_prefix != '':
            print( 'Sending discovery information' )
            data = {
                    "availability_topic": self.discovery_prefix + "homeeasy",
                    "payload_on": "on",
                    "payload_off": "off",
                    "state_on": "on",
                    "state_off": "off",
                    "retain": "true",

                    "payload_available": "online",
                    "payload_not_available": "offline",
                    }

            for switch in self.homeeasy.switches:
                key = self.discovery_prefix + 'switch/homeeasy/' + 'homeeasy_switch_' + str( switch.id ) + '/config'
                data["command_topic"] = switch_topic = self.prefix + 'homeeasy_switch_' + str( switch.id ) + '/set'
                data["state_topic"] = switch_topic = self.prefix + 'homeeasy_switch_' + str( switch.id ) + '/state'
                data["unique_id"] = "homeeasy_dev_" + str( switch.id )
                data["name"] = switch.name

                print( '    Registering: ' + switch.name )
                self.client.publish( key, payload = json.dumps( data ), retain = True )
                self.topic_mapping[ 'homeeasy_switch_' + str( switch.id ) ] = switch.id

            print( 'Going online for HA' )
            self.client.publish( self.discovery_prefix + 'homeeasy', 'online', retain = True )
            self.client.will_set( self.discovery_prefix + 'homeeasy', 'offline', retain = True )

    def disconnect( self ):
        print( 'Shutting down' )
        if self.discovery_prefix != '':
            self.client.publish( self.discovery_prefix + 'homeeasy', 'offline', retain = True )
            time.sleep( 0.5 )
        self.client.disconnect()

    def on_message( self, client, userdata, msg ):
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
            he_key = topic[0]
            if he_key in self.topic_mapping:
                he_key = self.topic_mapping[he_key]

            if topic[1] == 'set':
                self.client.publish( self.prefix + topic[0] + '/state', ( 'on' if value else 'off' ), retain = True )
                self.homeeasy.set_state( 'switch', he_key, value, None )
            elif topic[1] in ( 'config', 'state' ):
                pass
            else:
                print( 'Unknown topic: ' + '/'.join( topic ) )
        elif len( topic ) == 1:
            if topic[0] in self.topic_mapping:
                self.data[ self.topic_mapping[ topic[ 0 ] ] ] = value
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
MQTT_PREFIX                 = os.getenv( 'MQTT_PREFIX',            'homeassistant/switch/homeeasy' )

MQTT_HA_DISCOVERY           = os.getenv( 'MQTT_HA_DISCOVERY',      '' )

HOMEEASY_ADDRESS            = os.getenv( 'HOMEEASY_ADDRESS',       'homeeasy.lan' )
HOMEEASY_USER               = os.getenv( 'HOMEEASY_USER',          'admin' )
HOMEEASY_PASSWORD_HASH      = os.getenv( 'HOMEEASY_PASSWORD_HASH', '96e79218965eb72c92a549dd5a330112' )

client = mqtt.Client()
persistence = MqttPersistence( MQTT_PREFIX, client )
ha = homeeasy.HomeEasy( HOMEEASY_ADDRESS, HOMEEASY_USER, HOMEEASY_PASSWORD_HASH, persistence )
persistence.set_homeeasy( ha, MQTT_HA_DISCOVERY )

client.connect( MQTT_BROKER, 1883, 60 )

try:
    client.loop_forever()
except KeyboardInterrupt:
    persistence.disconnect()
