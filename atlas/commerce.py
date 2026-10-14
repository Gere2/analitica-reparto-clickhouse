"""Synthetic commerce domain. Checkout is the only source of customer orders."""
import random
from datetime import timedelta
from uuid import UUID,uuid5
from atlas.contract import validate
from atlas.operations import validate_operation
from atlas.simulation import iso,distance,interpolate,restaurant_location

ZERO='00000000-0000-0000-0000-000000000000'
ACTIONS={'search','open_restaurant','open_product','add_to_cart','remove_from_cart','checkout','abandon'}


class CommerceEngine:
    """Pure state transition engine; caller commits its copy only after queue acceptance."""
    def __init__(self,run_id,start,fleet,customers,seed,catalog,mode,model=None):
        self.run_id=str(UUID(run_id));self.namespace=UUID(run_id)
        self.start=start;self.mode=mode;self.model=model;self.seed=seed
        self.shops={s['restaurant_id']:s for s in catalog['restaurants']}
        self.products={p['product_id']:p for p in catalog['products']}
        if not self.shops or not self.products:raise ValueError('El catálogo de demo está vacío.')
        self.customers={};self.couriers={};self.orders={};self.tick=0
        for i in range(customers):
            cid=self.uid('customer',i)
            budget=1400+(i%4)*400
            self.customers[cid]={'customer_id':cid,'index':i,'label':f'Cliente {i+1:02}',
                'decision_mode':('ollama' if i<3 else 'traffic') if mode=='hybrid' else mode,
                'traffic_next_at':start+timedelta(seconds=random.Random(seed+i).uniform(0,8)),
                'budget':budget,'objective':f'Quiero cenar por menos de {budget/100:.2f} EUR y comprar una opción que me convenga.',
                'cycle':0,'revision':0,'stage':'idle','restaurant_id':None,'product_id':None,
                'cart':{},'steps':0,'order_id':None,'ready_at':start,'session_id':self.uid('session',i,0)}
        for i in range(fleet):
            cid=self.uid('courier',i)
            origin=restaurant_location(i);rng=random.Random(f'{seed}:courier:{i}')
            position=(origin[0]+rng.uniform(-.002,.002),origin[1]+rng.uniform(-.003,.003))
            self.couriers[cid]={'id':cid,'position':position,'order_id':None}

    def uid(self,*parts):return str(uuid5(self.namespace,':'.join(map(str,parts))))

    def total(self,customer):
        return sum(self.products[p]['price_minor']*q for p,q in customer['cart'].items())

    def context(self,cid,at):
        c=self.customers[cid]
        if c['ready_at']>at or c['stage'] in {'waiting_delivery','abandoned','delivered'}:return None
        remaining=c['budget']-self.total(c)
        # Compact candidate catalog; identifiers are resolved by Python, never invented by the model.
        shops=list(self.shops.values())
        pool=[shops[(c['index']+n)%len(shops)] for n in range(min(3,len(shops)))]
        restaurant_choices=[{'name':s['name'],'id':s['restaurant_id']} for s in pool]
        if c['cart']:
            restaurant_choices=[r for r in restaurant_choices if r['id']==c['restaurant_id']]
        product_choices=[{'name':p['product_name'][:90],'price_minor':p['price_minor'],'id':p['product_id']}
            for p in self.products.values() if p['restaurant_id']==c['restaurant_id'] and p['price_minor']<=remaining]
        choices={}
        stage=c['stage']
        if stage=='idle':allowed=['search']
        elif stage=='results':allowed=['open_restaurant','abandon'];choices['open_restaurant']=restaurant_choices
        elif stage=='restaurant':
            allowed=['open_restaurant','abandon'];choices['open_restaurant']=restaurant_choices
            if product_choices:allowed.insert(0,'open_product');choices['open_product']=product_choices
        elif stage=='product':
            allowed=['open_product','open_restaurant','abandon']
            choices.update(open_product=product_choices,open_restaurant=restaurant_choices)
            p=self.products.get(c['product_id'])
            if p and p['price_minor']<=remaining and sum(c['cart'].values())<5:
                allowed.insert(0,'add_to_cart')
            if not product_choices:allowed.remove('open_product')
        elif stage=='cart':
            allowed=['checkout','remove_from_cart','abandon']
            choices['remove_from_cart']=[{'id':p,'name':self.products[p]['product_name'][:90]} for p in c['cart']]
            if product_choices and sum(c['cart'].values())<5:
                allowed.insert(1,'open_product');choices['open_product']=product_choices
        else:raise ValueError('Estado de cliente inválido.')
        return {'customer_index':c['index'],'objective':c['objective'],'budget_minor':c['budget'],
            'stage':stage,'steps':c['steps'],'cart_total_minor':self.total(c),
            'cart':[{'name':self.products[p]['product_name'][:90],'quantity':q} for p,q in c['cart'].items()],
            'allowed':allowed,'choices':choices,'revision':c['revision']}

    def activity(self,c,at,action,reason,mode=None):
        mode=mode or c['decision_mode']
        return {'_stream':'customer_activity','schema_version':1,
            'event_id':self.uid('activity',c['customer_id'],c['revision']),
            'simulation_run_id':self.run_id,'customer_id':c['customer_id'],'session_id':c['session_id'],
            'event_time':iso(at),'customer_label':c['label'],'objective':c['objective'],
            'budget_minor':c['budget'],'action':action,'stage':c['stage'],'reason':reason,
            'restaurant_id':c['restaurant_id'],'product_id':c['product_id'],'order_id':c['order_id'],
            'cart_total_minor':self.total(c),'decision_mode':mode,
            'model':self.model if mode=='ollama' else None,'source_kind':'synthetic'}

    def decide(self,cid,revision,decision,at):
        c=self.customers[cid];context=self.context(cid,at)
        if not context or revision!=c['revision']:return []
        if not isinstance(decision,dict) or set(decision)!={'action','choice','reason'}:
            raise ValueError('La decisión debe contener action, choice y reason.')
        action=decision['action'];index=decision['choice'];reason=decision['reason']
        if action not in context['allowed'] or type(index) is not int or index<0 or not isinstance(reason,str) or not 0<len(reason)<=240:
            raise ValueError('Acción, opción o explicación no permitidas.')
        options=context['choices'].get(action,[])
        if (options and index>=len(options)) or (not options and index!=0):
            raise ValueError('La opción no pertenece al catálogo visible.')
        choice=options[index] if options else None
        mode=c['decision_mode']
        if c['steps']>=14:action='abandon';reason='Límite de pasos por sesión alcanzado.';mode='system'
        c['revision']+=1;c['steps']+=1
        mapping={'search':'search','open_restaurant':'restaurant_opened','open_product':'product_opened',
            'add_to_cart':'cart_added','remove_from_cart':'cart_removed','checkout':'order_submitted','abandon':'session_abandoned'}
        if action=='search':c['stage']='results'
        elif action=='open_restaurant':
            if c['cart'] and c['restaurant_id']!=choice['id']:
                raise ValueError('No cambiar de restaurante con un carrito abierto.')
            c['restaurant_id']=choice['id'];c['product_id']=None;c['stage']='restaurant'
        elif action=='open_product':c['product_id']=choice['id'];c['stage']='product'
        elif action=='add_to_cart':
            p=c['product_id'];c['cart'][p]=c['cart'].get(p,0)+1;c['stage']='cart'
        elif action=='remove_from_cart':
            p=choice['id'];c['product_id']=p;c['cart'][p]-=1
            if not c['cart'][p]:del c['cart'][p]
            c['stage']='cart' if c['cart'] else 'restaurant'
        elif action=='abandon':c['stage']='abandoned';c['ready_at']=at+timedelta(seconds=8)
        elif action=='checkout':
            if not c['cart'] or self.total(c)>c['budget']:raise ValueError('Carrito vacío o fuera de presupuesto.')
            if sum(o['status'] not in {'delivered','cancelled'} for o in self.orders.values())>=max(100,len(self.customers)*2):
                raise ValueError('La operación tiene demasiados pedidos pendientes.')
            c['order_id']=self.uid('order',c['session_id']);c['stage']='waiting_delivery'
        nav=validate({'schema_version':1,'event_id':self.uid('click',cid,c['revision']),
            'session_id':c['session_id'],'user_id':cid,'event_time':iso(at),'event_type':mapping[action],
            'section':{'search':'search','open_restaurant':'restaurants','open_product':'menu','add_to_cart':'cart',
                'remove_from_cart':'cart','checkout':'checkout','abandon':'session'}[action],
            'city_id':'madrid','restaurant_id':c['restaurant_id'],'product_id':c['product_id'],
            'order_id':c['order_id'],'source':'atlas-customer-'+mode,'source_kind':'synthetic','simulation_run_id':self.run_id})
        rows=[nav,self.activity(c,at,action,reason,mode)]
        if action=='checkout':
            oid=c['order_id'];rng=random.Random(oid);shop=self.shops[c['restaurant_id']]
            pickup=(shop['latitude'],shop['longitude']);dropoff=(pickup[0]+rng.uniform(-.003,.003),pickup[1]+rng.uniform(-.004,.004))
            order={'id':oid,'customer_id':cid,'restaurant_id':c['restaurant_id'],'created':at,
                'pickup':pickup,'dropoff':dropoff,'amount':self.total(c),'status':'created',
                'courier_id':None,'assigned_at':None,'sequence':0,'last_marker':None}
            self.orders[oid]=order
            rows.append({'_stream':'customer_orders','schema_version':1,'event_id':self.uid('purchase',oid),
                'simulation_run_id':self.run_id,'order_id':oid,'customer_id':cid,'session_id':c['session_id'],
                'checkout_event_id':nav['event_id'],'event_time':iso(at),'restaurant_id':c['restaurant_id'],
                'items':[[p,q,self.products[p]['price_minor']] for p,q in c['cart'].items()],
                'amount_minor':order['amount'],'currency':'EUR','decision_mode':mode,'source_kind':'synthetic'})
            rows.append(self.order_event(order,at))
        return rows

    def order_event(self,o,at):
        o['sequence']+=1;o['last_marker']=(o['status'],o['courier_id'])
        return validate_operation('order_events',{'schema_version':1,'event_id':self.uid('order-state',o['id'],o['sequence']),
            'simulation_run_id':self.run_id,'event_time':iso(at),'city_id':'madrid','order_id':o['id'],
            'courier_id':o['courier_id'] or ZERO,'restaurant_id':o['restaurant_id'],'status':o['status'],
            'amount_minor':o['amount'],'currency':'EUR','pickup_lat':o['pickup'][0],'pickup_lon':o['pickup'][1],
            'dropoff_lat':o['dropoff'][0],'dropoff_lon':o['dropoff'][1],'order_created_at':iso(o['created']),
            'promised_delivery_at':iso(o['created']+timedelta(seconds=120)),
            'source':'atlas-customer-delivery','source_kind':'synthetic'})

    def advance(self,at):
        rows=[];self.tick+=1
        for c in self.customers.values():
            if c['stage'] in {'abandoned','delivered'} and at>=c['ready_at']:
                c.update(cycle=c['cycle']+1,stage='idle',restaurant_id=None,product_id=None,cart={},steps=0,order_id=None)
                c['session_id']=self.uid('session',c['index'],c['cycle']);c['revision']+=1;c['registered']=False
            if not c.get('registered'):
                c['registered']=True;c['revision']+=1
                rows.append(self.activity(c,at,'session_started','Comienza una sesión de cliente ficticio.','system'))
        for o in list(self.orders.values()):
            if o['status'] in {'delivered','cancelled'}:continue
            if not o['courier_id']:
                free=[v for v in self.couriers.values() if not v['order_id']]
                if free:
                    courier=min(free,key=lambda v:distance(v['position'],o['pickup']))
                    o.update(courier_id=courier['id'],assigned_at=at,origin=courier['position'])
                    courier['order_id']=o['id']
            if o['assigned_at']:
                elapsed=(at-o['assigned_at']).total_seconds()
                o['status']='created' if elapsed<8 else 'preparing' if elapsed<30 else 'picked_up' if elapsed<35 else 'en_route' if elapsed<95 else 'delivered'
                courier=self.couriers[o['courier_id']]
                if elapsed<30:position=interpolate(o['origin'],o['pickup'],elapsed/30)
                else:position=interpolate(o['pickup'],o['dropoff'],(elapsed-35)/60)
                courier['position']=position
                if o['status']=='delivered':
                    c=self.customers[o['customer_id']];c['stage']='delivered';c['revision']+=1;c['ready_at']=at+timedelta(seconds=12)
                    rows.append(self.activity(c,at,'delivery_completed','El pedido confirmado por este cliente se ha entregado.','system'))
            if (o['status'],o['courier_id'])!=o['last_marker']:rows.append(self.order_event(o,at))
        for courier in self.couriers.values():
            oid=courier['order_id'];o=self.orders.get(oid);speed=0
            if o and o['assigned_at']:
                elapsed=(at-o['assigned_at']).total_seconds()
                speed=min(140,distance(o['origin'],o['pickup'])/30*3.6) if elapsed<30 else min(140,distance(o['pickup'],o['dropoff'])/60*3.6) if 35<=elapsed<95 else 0
            rows.append(validate_operation('courier_positions',{'schema_version':1,'event_id':self.uid('gps',courier['id'],self.tick),
                'simulation_run_id':self.run_id,'event_time':iso(at),'city_id':'madrid','courier_id':courier['id'],
                'order_id':oid or ZERO,'latitude':round(courier['position'][0],7),'longitude':round(courier['position'][1],7),
                'speed_kmh':round(speed,2),'accuracy_m':5.0,'source':'atlas-customer-delivery','source_kind':'synthetic'}))
            if o and o['status']=='delivered':courier['order_id']=None
        # Keep operational memory bounded; historical truth remains in ClickHouse.
        for oid,o in list(self.orders.items()):
            if o['status']=='delivered' and at-o['created']>timedelta(minutes=5):del self.orders[oid]
        return rows
