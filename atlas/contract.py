"""Versioned event contract. No inferred relationships between public datasets."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

ACTIONS = {'search', 'filter_applied', 'restaurant_opened', 'product_opened',
           'product_impression', 'cart_added', 'order_submitted'}
KINDS = {'synthetic', 'demo_live', 'public_historical', 'historical_replay'}
REQUIRED = {'schema_version', 'event_id', 'session_id', 'event_time', 'event_type',
            'section', 'city_id', 'source', 'source_kind'}
OPTIONAL = {'user_id', 'restaurant_id', 'product_id', 'source_record_id', 'simulation_run_id'}

def validate(event):
    if not isinstance(event, dict):
        raise ValueError('Cada evento debe ser un objeto JSON.')
    if REQUIRED - event.keys() or event.keys() - REQUIRED - OPTIONAL:
        raise ValueError('Campos obligatorios ausentes o campos desconocidos.')
    if type(event['schema_version']) is not int or event['schema_version'] != 1:
        raise ValueError('schema_version debe ser 1.')
    out = dict(event)
    for key in REQUIRED - {'schema_version'}:
        if not isinstance(out[key], str) or not 0 < len(out[key]) <= 160 or '\x00' in out[key]:
            raise ValueError(f'{key}: cadena obligatoria, máximo 160 caracteres.')
    for key in ('event_id', 'session_id'):
        out[key] = str(UUID(out[key]))
    if out['event_type'] not in ACTIONS or out['source_kind'] not in KINDS:
        raise ValueError('Acción o procedencia no admitida.')
    at = datetime.fromisoformat(out['event_time'].replace('Z', '+00:00'))
    if at.tzinfo is None:
        raise ValueError('event_time debe incluir zona horaria.')
    at = at.astimezone(timezone.utc)
    if not datetime(2000, 1, 1, tzinfo=timezone.utc) <= at <= datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('Fecha fuera del intervalo admitido (2000 hasta ahora + 5 minutos).')
    out['event_time'] = at.isoformat(timespec='milliseconds')
    for key in OPTIONAL:
        value = out.get(key)
        if value is not None and (not isinstance(value, str) or not 0 < len(value) <= 160 or '\x00' in value):
            raise ValueError(f'{key}: cadena de hasta 160 caracteres o null.')
        out[key] = value
    if out['simulation_run_id'] is not None:
        out['simulation_run_id'] = str(UUID(out['simulation_run_id']))
    if out['source_kind'] == 'synthetic' and not out['simulation_run_id']:
        raise ValueError('La simulación necesita simulation_run_id.')
    if out['source_kind'] in {'public_historical', 'historical_replay'} and not out['source_record_id']:
        raise ValueError('Una fuente histórica necesita source_record_id.')
    if out['event_type'] in {'restaurant_opened', 'product_opened', 'product_impression', 'cart_added', 'order_submitted'} and not out['restaurant_id']:
        raise ValueError('Esta acción necesita restaurant_id.')
    if out['event_type'] in {'product_opened', 'product_impression', 'cart_added'} and not out['product_id']:
        raise ValueError('Esta acción necesita product_id.')
    return out
