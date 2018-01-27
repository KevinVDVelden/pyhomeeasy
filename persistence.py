import json

class JsonPersistence:
    def __init__( self, filename ):
        self.filename = filename

        try:
            self.data = json.load( open( self.filename, 'r' ) )
        except:
            self.data = {}

    def get( self, key ):
        val = self.data

        for key_part in key:
            if key_part in val:
                val = val[ key_part ]
            else:
                return None

        return val

    def set( self, key, new_value ):
        val = self.data
        for key_part in key[:-1]:
            if key_part not in val:
                val[ key_part ] = {}

            val = val[ key_part ]

        val[ key[ -1 ] ] = new_value

        json.dump( self.data, open( self.filename, 'w' ) )


