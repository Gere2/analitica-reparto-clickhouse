"""Clock-driven synthetic Madrid fleet; the dashboard only reads ClickHouse."""
import math
import random
import threading
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4, uuid5
from atlas.operations import validate_operation

def iso(at):
    return at.astimezone(timezone.utc).isoformat(timespec='milliseconds')

def distance(a,b):
    lat=math.radians((a[0]+b[0])/2)
    return math.hypot((a[0]-b[0])*111320,(a[1]-b[1])*111320*math.cos(lat))

def interpolate(a,b,t):
    t=max(0,min(1,t))
    return (a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)

def restaurant_location(index):
    rng=random.Random(f'atlas-restaurant:{index%12}')
    return (40.409+rng.random()*.014,-3.710+rng.random()*.018)

class Scenario:
    """Deterministic snapshots from a run, seed and wall-clock tick."""
    def __init__(self,run_id,start,fleet=12,seed=42):
        self.run_id=str(UUID(run_id))
        self.namespace=UUID(run_id)
        self.start,self.fleet,self.seed=start,fleet,seed
        self.previous_status={}

    def sample(self,at):
        positions,orders,clicks=[],[],[]
        elapsed=max(0,(at-self.start).total_seconds())
        for n in range(self.fleet):
            offset=n*160/self.fleet
            tick=elapsed+offset
            cycle=int(tick//160)
            phase=tick%160
            rng=random.Random(f'{self.seed}:{n}:{cycle}')
            pickup=restaurant_location(n)
            dropoff=(pickup[0]+rng.uniform(-.003,.003),pickup[1]+rng.uniform(-.004,.004))
            origin=(pickup[0]-.0008,pickup[1]-.001)
            if cycle:
                previous=random.Random(f'{self.seed}:{n}:{cycle-1}')
                previous_dropoff=(pickup[0]+previous.uniform(-.003,.003),pickup[1]+previous.uniform(-.004,.004))
                origin=pickup if previous.random()<.12 else previous_dropoff
            corner=(pickup[0],dropoff[1])
            cancelled=rng.random()<.12
            if cancelled and phase>=35:
                status='cancelled'
            else:
                status='created' if phase<8 else 'preparing' if phase<35 else 'picked_up' if phase<40 else 'en_route' if phase<140 else 'delivered'
            if phase<35 or status=='cancelled':
                position=interpolate(origin,pickup,phase/35)
                speed=distance(origin,pickup)/35*3.6 if status!='cancelled' else 0
            elif phase<40:
                position=pickup
                speed=0
            else:
                progress=(phase-40)/100
                position=interpolate(pickup,corner,progress*2) if progress<.5 else interpolate(corner,dropoff,(progress-.5)*2)
                speed=(distance(pickup,corner)+distance(corner,dropoff))/100*3.6 if phase<140 else 0
            courier=str(uuid5(self.namespace,f'courier:{n}'))
            order=str(uuid5(self.namespace,f'order:{n}:{cycle}'))
            created=self.start+timedelta(seconds=cycle*160-offset)
            common={'schema_version':1,'simulation_run_id':self.run_id,'event_time':iso(at),
                'city_id':'madrid','courier_id':courier,'order_id':order,'source':'atlas-fleet-simulator','source_kind':'synthetic'}
            positions.append(validate_operation('courier_positions',dict(common,
                event_id=str(uuid5(self.namespace,f'gps:{n}:{iso(at)}')),
                latitude=round(position[0],7),longitude=round(position[1],7),
                speed_kmh=round(speed,2),accuracy_m=5.0)))
            marker=(cycle,status)
            if self.previous_status.get(n)!=marker:
                self.previous_status[n]=marker
                restaurant=f'fictional-madrid-{n%12+1}'
                orders.append(validate_operation('order_events',dict(common,
                    event_id=str(uuid5(self.namespace,f'status:{n}:{cycle}:{status}')),
                    restaurant_id=restaurant,status=status,amount_minor=rng.randint(950,4500),currency='EUR',
                    pickup_lat=pickup[0],pickup_lon=pickup[1],dropoff_lat=dropoff[0],dropoff_lon=dropoff[1],
                    order_created_at=iso(created),promised_delivery_at=iso(created+timedelta(seconds=125)))))
                if self.previous_status.get(('click',n))!=cycle:
                    self.previous_status[('click',n)]=cycle
                    # Independent navigation sample; not an observed customer journey for this order.
                    session=str(uuid5(self.namespace,f'session:{n}:{cycle}'))
                    for step,action in enumerate(['search','restaurant_opened','product_opened','cart_added','order_submitted']):
                        if rng.random()<.12:
                            break
                        clicks.append({'schema_version':1,'event_id':str(uuid5(self.namespace,f'click:{n}:{cycle}:{step}')),
                            'session_id':session,'event_time':iso(at),'event_type':action,
                            'section':['search','restaurants','menu','cart','checkout'][step],'city_id':'madrid',
                            'restaurant_id':restaurant,'product_id':f'{restaurant}-product-1',
                            'source':'atlas-fleet-simulator','source_kind':'synthetic','simulation_run_id':self.run_id})
        return positions,orders,clicks

class Simulator:
    def __init__(self,store):
        self.store=store
        self.lock=threading.RLock()
        self.thread=None
        self.cancel=threading.Event()
        previous=store.metadata('simulation') or {}
        self.state=dict(previous,running=False,state='stopped',error=None)

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def start(self,fleet=12,interval=2,seed=42):
        if type(fleet) is not int or not 1<=fleet<=50 or type(interval) not in (int,float) or not 1<=interval<=10:
            raise ValueError('Usar 1 a 50 repartidores e intervalo de 1 a 10 segundos.')
        if type(seed) is not int or not 0<=seed<=4294967295:
            raise ValueError('Semilla entera entre 0 y 4294967295.')
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError('La simulación ya está activa; pararla antes de iniciar otra.')
            self.cancel=threading.Event()
            now=datetime.now(timezone.utc)
            self.scenario=Scenario(str(uuid4()),now,fleet,seed)
            self.state={'run_id':self.scenario.run_id,'started_at':iso(now),'fleet':fleet,
                'interval_seconds':interval,'seed':seed,'running':True,'state':'running',
                'ticks':0,'accepted':0,'error':None,'last_tick_at':None,
                'meaning':'Posiciones y pedidos sintéticos en tiempo de reloj; rutas esquemáticas.'}
            self.store.metadata('simulation',self.state)
            self.thread=threading.Thread(target=self.run,daemon=True)
            self.thread.start()
            return dict(self.state)

    def stop(self):
        with self.lock:
            self.cancel.set()
            thread=self.thread
        if thread:
            thread.join(3)
        return self.snapshot()

    def run(self):
        from atlas.contract import validate
        deadline=time.monotonic()
        previous_tick=None
        try:
            while not self.cancel.is_set():
                now=datetime.now(timezone.utc)
                gps,orders,clicks=self.scenario.sample(now)
                events=gps+orders+[validate(e) for e in clicks]
                result=self.store.accept(events)
                with self.lock:
                    self.state['ticks']+=1
                    self.state['accepted']+=result['accepted']
                    self.state['last_tick_at']=iso(now)
                    self.state['observed_interval_seconds']=None if previous_tick is None else round((now-previous_tick).total_seconds(),3)
                previous_tick=now
                deadline=max(deadline+self.state['interval_seconds'],time.monotonic())
                self.cancel.wait(max(0,deadline-time.monotonic()))
        except Exception as error:
            with self.lock:
                self.state['error']=str(error)[:300]
        finally:
            with self.lock:
                self.state['running']=False
                self.state['state']='error' if self.state['error'] else 'stopped'
                self.store.metadata('simulation',self.state)
