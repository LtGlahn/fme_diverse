"""
Verifiserer at vi får samme data fra nytt vegreferanse-endepunkt som vi får fra visveeginfo
"""
# import requests
import apiforbindelse
from datetime import datetime
import os

import pandas as pd 
import geopandas as gpd 
from shapely import wkt 
from shapely.geometry import LineString 

apiurl = 'https://nvdbapiles-v3.test.atlas.vegvesen.no/'

def hentlabsysdata( filnavn, layer ): 

    data = gpd.read_file( filnavn, layer=layer )

    # Stakkars to_datetime funksjonen får hikke av datoen 9999-12-31
    data.replace( to_replace='9999-12-31', value='2025-12-31', inplace=True )

    # Tonnevis med duplikater, ignorerer 
    data = data[ ~data.duplicated( subset=['labsys_VEGREFERANSE', 'labsys_OPPRETTET_DATO'] ) ]

    # Ignorerer data der labsys sjøl har introdusert flertydighet ved å operere med snåle fylkesnummer
    data = data[ data['labsys_FYLKE_KODE'].isin( [ 1,2,3,4,5,6,7,8,9,10,11,12,14,15,18,19,20,50 ] ) ].copy()

    data['antattRegistreringsdato'] = pd.to_datetime( data['labsys_OPPRETTET_DATO'], infer_datetime_format=True ) 
    data['vvi_fradato']             = pd.to_datetime( data['ValidFrom'], infer_datetime_format=True )
    data['vvi_tildato']             = pd.to_datetime( data['ValidTo'], infer_datetime_format=True )

    data = data[ ( data['antattRegistreringsdato'] >= data['vvi_fradato'] ) & ( data['antattRegistreringsdato'] < data['vvi_tildato'])  ].copy()
    data['tidspunkt'] = data['antattRegistreringsdato'].apply( lambda x : x.isoformat()[0:10] )

    data.reset_index( inplace=True )

    return data 

def hentCSVeksempler( filnavn ):

    data = pd.read_csv( filnavn)
    data = gpd.GeoDataFrame( data, geometry=gpd.points_from_xy( data['X'], data['Y']), crs=5973 )


    data['vref_FYLKE']      = data['vegreferanse'].apply(  lambda x : int( x[0:2] ))
    data['vref_KOMMUNE']    = data['vegreferanse'].apply(  lambda x : int( x[2:4] ))
    data['vref_VEGKAT']     = data['vegreferanse'].apply(  lambda x :      x[4].upper() )
    data['vref_VEGSTATUS']  = data['vegreferanse'].apply(  lambda x :      x[5].upper() )
    data['vref_VEGNR']      = data['vegreferanse'].apply(  lambda x : int( x[6:].upper().split('H')[0] ))
    data['vref_HP']         = data['vegreferanse'].apply(  lambda x : int( x[6:].upper().split('P')[1].split('M')[0] ))
    data['vref_M']          = data['vegreferanse'].apply(  lambda x : int( x[6:].upper().split('P')[1].split('M')[1] ))

    
    data['labsys_VEGREFERANSE'] = data['vegreferanse']
        
    return data 

def sjekkvegreferanser( ref1, ref2): 
    ref1 = ref1.lower()
    ref2 = ref2.lower()

    r1 = ref1.split( 'm')
    r2 = ref2.split( 'm')
    m1 = int( r1[1] )
    m2 = int( r2[1])
    differanse = abs( m2-m1 )

    if ref1 == ref2: 
        return 'OK'
    elif r1[0] == r2[0] and differanse < 1.5: 
        return 'Innafor metern'
    else: 
        return 'FEILER'

def sammenlignStedfesting( vpos1, vpos2 ): 
    """
    Sjekker at to veglenkeposisjoner er identiske
    """

    p1, v1 = vpos1.split( '@' )
    p2, v2 = vpos2.split( '@' )

    pdiff = abs( float( p2 ) - float( p1 ) )

    if v1 != v2: 
        return 'Ulike veglenkesekvenser'
    elif pdiff == 0: 
        return 'Eksakt match veglenkeposisjon'
    elif pdiff < 1.e-9: 
        return 'Veglenkeposisjon avvik 9. siffer'
    elif pdiff < 1.e-8: 
        return 'Veglenkeposisjon avvik 8. siffer'
    elif pdiff < 1.e-7: 
        return 'Veglenkeposisjon avvik 7. siffer'
    elif pdiff < 1.e-6: 
        return 'Veglenkeposisjon avvik 6. siffer'
    elif pdiff < 1.e-5: 
        return 'Veglenkeposisjon avvik 5. siffer'
    elif pdiff < 1.e-4: 
        return 'Veglenkeposisjon avvik 4. siffer'
    elif pdiff >= 1.e-4: 
        return 'Veglenkeposisjon avvik >= 3. siffer'
    else: 
        return f"Rar verdi ved sammenligning av veglenkeposisjoner {vpos1} og {vpos2}"

    return f"VELDIG rar verdi ved sammenligning av veglenkeposisjoner {vpos1} og {vpos2}"


if __name__ == '__main__': 

    t0 = datetime.now( )
    forb = apiforbindelse.apiforbindelse()

    ## Henter data fra labsys kvalink rekonstruksjon 
    data2 = hentlabsysdata( 'labsys_vegsystemreferanse_PROD-v1.gpkg', 'labsys_oppfrisk_vegreferanser' )
    resultatGPKG = 'testvegrefapi-ATM_tirsdag13des.gpkg'    

    ##  Henter sammple data fra 
    # data2 = hentCSVeksempler( 'eksempler_snuddmetrering.csv')
    # resultatGPKG = 'testvegrefapi-ATMv-snudd3.gpkg'

    
    resultater = []
    feiler =     []
    feiler2 =    []

    print( f"Datainnlesing og prepping tok litt tid: {datetime.now()-t0} ")

    for ii, row in data2.iterrows():

        if ii % 100 == 0 or ii in [0, 5, 10, 50]: 
            print( f"Prosesser rad {ii} av {len(data2)} "  )

        # tmp = row['labsys_OPPRETTET_DATO'].split('.')
        # tmp.reverse()
        # tidspunkt = '-'.join( tmp ) # Gjør om denne! 

        kartvisning = 'https://labs.vegdata.no/vegrefendring/?kartvisning=vegreferanse&fylke=' + str( row['vref_FYLKE'] ) +  '&kommune=' + str(  row['vref_KOMMUNE'] ) + \
                    '&vegkat='  + row['vref_VEGKAT'] +  '&vegstatus=' + row['vref_VEGSTATUS'] + '&vegnr=' + str(row['vref_VEGNR']) +  '&hp=' + str( row['vref_HP']) + \
                        '&meter=' + str( row['vref_M'] ) + '&dato=' + row['tidspunkt']

        # r = requests.get( apiurl, params={ 'vegreferanse' : row['labsys_VEGREFERANSE'], 'tidspunkt' : tidspunkt  })
        r = forb.les( apiurl + 'vegreferanseposisjon', params={ 'vegreferanse' : row['labsys_VEGREFERANSE'], 'tidspunkt' : row['tidspunkt']  })
        if r.ok: 
            respons = r.json()
            if len( respons ) == 1: 
                p1 = wkt.loads( respons[0]['geometri']['wkt'])
                avstand = p1.distance( row['geometry'])
                if avstand > 0.5: 
                    geom = LineString( [ [p1.x, p1.y], [row['geometry'].x, row['geometry'].y]  ])

                else: 
                    geom = p1 


                resultat = { 'avstand VVI-LES' : avstand, 
                             'tidspunkt' : row['tidspunkt'], 
                             'vegreferanse' : row['labsys_VEGREFERANSE'].lower(), 
                             'vegsystemreferanse' : respons[0]['vegsystemreferanse']['kortform'], 
                             'kartvisning' : kartvisning, 
                             'url' : r.url,
                             'veglenkepos' : respons[0]['veglenkesekvens']['kortform'],
                             'geometry' : geom   }

                if 'kommentar' in row: 
                    resultat['kommentar'] = row['kommentar']

                resultat['identiske_duplikatsvar'] = 'Ikke relevant'

                # TODO: 
                #  - Sjekk at vi får returnert samme veglenkesekvensposisjon som vi gir inn
                #  - Lag eget resultatsett med flere egenskaper. 

                # Sjekker at vi får samme svar ved oppslag på lenkesekvens 
                r2 = forb.les( apiurl + 'vegreferanse', params= { 'veglenkesekvens' : respons[0]['veglenkesekvens']['kortform'], 'tidspunkt' : row['tidspunkt']  } )
                if r2.ok: 
                    respons2 = r2.json()
                    if len( respons2 ) == 1: 
                        p2 = wkt.loads( respons2[0]['geometri']['wkt'] )
                        avstand2 = p2.distance( p1 )
                        resultat['Avstand veglenkepos-oppslag'] =  avstand2 
                        resultat['Veglenkepos vegreferanse-verdi'] = respons2[0]['vegreferanse']['kortform'].lower().replace( ' ', '') 

                         
                        resultat['Veglenkepos vegreferanse-sjekk'] = sjekkvegreferanser( resultat['Veglenkepos vegreferanse-verdi'], resultat['vegreferanse'] ) 
                        

                        resultat['sammenlignStedfesting'] = sammenlignStedfesting( respons[0]['veglenkesekvens']['kortform'], respons2[0]['veglenkesekvens']['kortform'] )
                        resultat['vpos1'] =  respons[0]['veglenkesekvens']['kortform']
                        resultat['vpos2'] = respons2[0]['veglenkesekvens']['kortform']


                        if avstand2 > 0.5: 
                            geom2 = LineString( [[p1.x, p1.y], [p2.x, p2.y]] )
                        else: 
                            geom2 = p2 
                        
                        if avstand2 > 0.5 or resultat['Veglenkepos vegreferanse-sjekk'] == 'FEILER' or resultat['sammenlignStedfesting'] != 'Eksakt match veglenkeposisjon': 

                            nyttObj = { 'vegreferanse orginal'                      : row['labsys_VEGREFERANSE'], 
                                        'veglenkepos'                               : respons[0]['veglenkesekvens']['kortform'], 
                                        'avstand vegrefoppslag - veglenkeoppslag'   : avstand2, 
                                        'vegreferanse veglenkeoppslag'              : resultat['Veglenkepos vegreferanse-verdi'], 
                                        'Veglenkepos vegreferanse-sjekk'            : resultat['Veglenkepos vegreferanse-sjekk'],
                                        'sammenlignStedfesting'                     : resultat['sammenlignStedfesting'],
                                        'vpos1'                                     : resultat['vpos1'],
                                        'vpos2'                                     : resultat['vpos2'],
                                        'geometry'                                  : geom2 
                                        }

                            feiler2.append( nyttObj )
                    else: 
                        resultat['Veglenkepos vegreferanse-sjekk'] = f"Oppslag på veglenkeposisjon gir {len( respons2 )} elementer i responsen "

                else: 
                    resultat['Veglenkepos vegreferanse-sjekk'] = f"Oppslag på veglenkeposisjon gir feilkode {r2.status_code} {r.text}"

                resultater.append( resultat )
            else: 

                print( f"Fikk {len(respons)} resultater fra spørring {r.url}\n\t{kartvisning} " )
                resultat =  {  'hva' : 'Feil antall svar-element', 'respons' : { 'data' : respons }, 'Antall element' : len( respons), 'url' : r.url, 'kartvisning' : kartvisning, 'geometry' : row['geometry'] }  
                if len( respons ) == 2 and respons[0] == respons[1]:
                    resultat['identiske_duplikatsvar'] = 'Ja'
                else: 
                    resultat['identiske_duplikatsvar'] = 'Nei'

                if 'kommentar' in row: 
                    resultat['kommentar'] = row['kommentar']

                feiler.append( resultat )
        else: 
            resultat =  { 'hva' : 'HTTP error', 'feilkode' : r.status_code, 'feilbeskrivelse' : r.text, 'url' : r.url, 'kartvisning' : kartvisning, 'geometry' : row['geometry'] } 
            if 'kommentar' in row: 
                resultat['kommentar'] = row['kommentar']

            feiler.append( resultat )




    try: 
        os.remove( resultatGPKG )
    except FileNotFoundError:
        pass  

    resultater = pd.DataFrame( resultater )
    resultater = gpd.GeoDataFrame( resultater, geometry='geometry', crs=5973 )
    resultater.to_file( resultatGPKG, layer='resultater', driver='GPKG' )

    feiler = pd.DataFrame( feiler )
    feiler = gpd.GeoDataFrame( feiler, geometry='geometry', crs=5973 )
    feiler.to_file( resultatGPKG, layer='feiler', driver='GPKG' )

    feiler2 = pd.DataFrame( feiler2)
    feiler2 = gpd.GeoDataFrame( feiler2, geometry='geometry', crs=5973 )
    feiler2.to_file( resultatGPKG, layer='vegposoppslagfeiler', driver='GPKG' )

    tid = datetime.now() - t0 
    print( f"Tidsbruk: {tid}" )
    print( 'resultatfil:', resultatGPKG )