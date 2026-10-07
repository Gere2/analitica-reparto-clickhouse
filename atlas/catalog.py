"""Seed 12 fictional restaurants and 36 products with field-level provenance."""
import json
import random
import time
from atlas.simulation import restaurant_location

NAMES=['Casa Río','Mesa Verde','Barrio Bento','La Cocina Azul','Horno Central','Taco Patio',
       'Cuchara Norte','Pasta de Casa','Curry del Barrio','Huerta y Pan','La Mesa Roja','Nómada Bowl']
FALLBACK=['Bowl de verduras','Menú de la casa','Ensalada del día']

def seed_demo_catalog(ch):
    if int(ch.query('SELECT count() AS n FROM delivery_atlas.demo_products FINAL')[0]['n'])==36 and int(ch.query('SELECT count() AS n FROM delivery_atlas.demo_restaurants FINAL')[0]['n'])==12:
        return
    products=[]
    if ch.query('EXISTS TABLE delivery.glovo_products')[0]['result']:
        products=ch.query("SELECT source_row,product_name FROM delivery.glovo_products WHERE "
            "country_code='ES' AND city_code='MAD' ORDER BY source_row LIMIT 36")
    shops,items=[],[]
    version=time.time_ns()
    rng=random.Random(42)
    for n,name in enumerate(NAMES):
        restaurant=f'fictional-madrid-{n+1}'
        lat,lon=restaurant_location(n)
        shops.append({'restaurant_id':restaurant,'name':name,'city_id':'madrid','latitude':lat,
            'longitude':lon,'location_kind':'synthetic','source_kind':'synthetic','version':version})
        for k in range(3):
            source=products[n*3+k] if len(products)==36 else None
            items.append({'product_id':f'{restaurant}-product-{k+1}','restaurant_id':restaurant,
                'product_name':source['product_name'] if source else FALLBACK[k],
                'price_minor':rng.randint(650,1800),'currency':'EUR','price_kind':'synthetic',
                'name_kind':'public_historical' if source else 'synthetic',
                'source_table':'delivery.glovo_products' if source else None,
                'source_row':source['source_row'] if source else None,'version':version})
    for table,rows in [('demo_restaurants',shops),('demo_products',items)]:
        ch.execute('INSERT INTO delivery_atlas.'+table+' FORMAT JSONEachRow\n'+'\n'.join(json.dumps(r,ensure_ascii=False) for r in rows))
