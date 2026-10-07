"""Contracts for synthetic delivery snapshots and GPS telemetry."""
import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

STATUSES = {'created', 'preparing', 'picked_up', 'en_route', 'delivered', 'cancelled'}
COMMON = {'schema_version','event_id','simulation_run_id','event_time','city_id',
          'courier_id','order_id','source','source_kind'}
FIELDS = {
    'courier_positions': COMMON | {'latitude','longitude','speed_kmh','accuracy_m'},
    'order_events': COMMON | {'restaurant_id','status','amount_minor','currency',
        'pickup_lat','pickup_lon','dropoff_lat','dropoff_lon','order_created_at','promised_delivery_at'},
}

def timestamp(value, allow_future=False):
    if not isinstance(value,str):
        raise ValueError('Fecha debe ser una cadena con zona horaria.')
    at = datetime.fromisoformat(value.replace('Z','+00:00'))
    if at.tzinfo is None:
        raise ValueError('Fecha debe incluir zona horaria.')
    at=at.astimezone(timezone.utc)
    ceiling=datetime.now(timezone.utc)+timedelta(days=1 if allow_future else 0,minutes=5)
    if not datetime(2000,1,1,tzinfo=timezone.utc)<=at<=ceiling:
        raise ValueError('Fecha fuera del intervalo permitido.')
    return at.isoformat(timespec='milliseconds')

def validate_operation(kind,event):
    if kind not in FIELDS or not isinstance(event,dict) or set(event)!=FIELDS[kind]:
        raise ValueError('Tipo de telemetría o campos incorrectos.')
    out=dict(event)
    if type(out['schema_version']) is not int or out['schema_version']!=1:
        raise ValueError('schema_version debe ser 1.')
    for key in ('event_id','simulation_run_id','courier_id','order_id'):
        if not isinstance(out[key],str):
            raise ValueError(key+': UUID requerido.')
        out[key]=str(UUID(out[key]))
    for key in ('city_id','source') + (('restaurant_id',) if kind=='order_events' else ()):
        if not isinstance(out[key],str) or not 0<len(out[key])<=160 or '\x00' in out[key]:
            raise ValueError(key+': cadena requerida de hasta 160 caracteres.')
    if out['source_kind']!='synthetic':
        raise ValueError('Esta telemetría de clase debe identificarse como synthetic.')
    out['event_time']=timestamp(out['event_time'])
    coords = [('latitude',90),('longitude',180)] if kind=='courier_positions' else [
        ('pickup_lat',90),('pickup_lon',180),('dropoff_lat',90),('dropoff_lon',180)]
    for key,limit in coords:
        if type(out[key]) not in (int,float) or not math.isfinite(out[key]) or not -limit<=out[key]<=limit:
            raise ValueError(key+': coordenada fuera de rango.')
        out[key]=float(out[key])
    if kind=='courier_positions':
        for key,limit in [('speed_kmh',150),('accuracy_m',10000)]:
            if type(out[key]) not in (int,float) or not math.isfinite(out[key]) or not 0<=out[key]<=limit:
                raise ValueError(key+': valor fuera de rango.')
            out[key]=float(out[key])
    else:
        if out['status'] not in STATUSES or out['currency']!='EUR':
            raise ValueError('Estado o moneda incorrectos.')
        if type(out['amount_minor']) is not int or not 0<=out['amount_minor']<=1000000:
            raise ValueError('amount_minor debe ser céntimos enteros entre 0 y 1000000.')
        out['order_created_at']=timestamp(out['order_created_at'])
        out['promised_delivery_at']=timestamp(out['promised_delivery_at'],allow_future=True)
        if out['order_created_at']>out['event_time'] or out['promised_delivery_at']<out['order_created_at']:
            raise ValueError('Horas del pedido inconsistentes.')
    # Internal routing participates in the immutable digest but is removed on INSERT.
    out['_stream']=kind
    return out
