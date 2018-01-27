import homeeasy
import sys

ha = homeeasy.HomeEasy( 'homeeasy.lan', 'admin', '96e79218965eb72c92a549dd5a330112' )
if len( sys.argv ) == 2:
    if sys.argv[1] in ( 'on', 'off' ):
        ha.switch( 'Rear Light' ).set_state( sys.argv[1] )
    elif sys.argv[1] == 'list':
        for room in ha.rooms:
            print( room.name )
            for switch in room.switches:
                print( '\t%s (%d)' % ( switch.name, switch.id ) )
if len( sys.argv ) == 3:
    ha.switch( sys.argv[1] ).set_state( sys.argv[2] )

