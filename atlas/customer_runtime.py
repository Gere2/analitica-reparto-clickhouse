"""Independent decision/GPS workers sharing a queue-committed commerce engine."""
import copy
import threading
import time
from datetime import datetime,timezone,timedelta
import random
import logging
from uuid import UUID,uuid4
from atlas.commerce import CommerceEngine
from atlas.customer_agent import OllamaAgent,PolicyAgent,TrafficAgent
from atlas.store import Full
from atlas.simulation import iso


class CustomerRuntime:
    def __init__(self,store,ch,fleet,customers,interval,seed,agent_mode):
        self.store=store;self.lock=threading.RLock();self.cancel=threading.Event()
        self.decider=OllamaAgent() if agent_mode in {'ollama','hybrid'} else PolicyAgent()
        self.traffic=TrafficAgent(seed)
        if agent_mode in {'ollama','hybrid'} and not self.decider.ready():
            raise ValueError('Modelo local no disponible. Arranca Ollama y descarga qwen3:0.6b; o elige política local.')
        catalog={'restaurants':ch.query('SELECT * EXCEPT version FROM delivery_atlas.demo_restaurants FINAL ORDER BY restaurant_id'),
            'products':ch.query('SELECT * EXCEPT version FROM delivery_atlas.demo_products FINAL ORDER BY product_id')}
        now=datetime.now(timezone.utc)
        self.engine=CommerceEngine(str(uuid4()),now,fleet,customers,seed,catalog,agent_mode,self.decider.model)
        self.state={'run_id':self.engine.run_id,'started_at':iso(now),'fleet':fleet,'customers':customers,
            'interval_seconds':interval,'seed':seed,'mode':'customers','agent_mode':agent_mode,
            'model':self.decider.model,'running':True,'state':'running','ticks':0,'accepted':0,
            'error':None,'agent_error':None,'decisions':0,'model_calls':0,'max_model_calls':120,
            'agent_state':'running','last_tick_at':None,
            'ai_customers':min(3,customers) if agent_mode=='hybrid' else customers if agent_mode=='ollama' else 0,
            'traffic_customers':max(0,customers-3) if agent_mode=='hybrid' else customers if agent_mode=='traffic' else 0,
            'traffic_decisions':0,'traffic_state':'running' if agent_mode in {'hybrid','traffic'} else 'inactive',
            'meaning':'Clientes sintéticos: checkout crea pedidos y su tracking. Compras sin cobro real.'}
        self.thread=threading.Thread(target=self.run,daemon=True)
        self.agent_thread=threading.Thread(target=self.agent_loop,daemon=True)
        self.traffic_thread=threading.Thread(target=self.traffic_loop,daemon=True)

    def snapshot(self):
        with self.lock:return dict(self.state)

    def commit(self,operation):
        # State is swapped only when the complete batch has been accepted by SQLite.
        # A failed/capacity-limited acceptance never creates a phantom purchase in memory.
        with self.lock:
            if self.cancel.is_set():return False
            candidate=copy.deepcopy(self.engine)
            rows=operation(candidate)
            if not rows:return False
            accepted=self.store.accept(rows)
            self.engine=candidate;self.state['accepted']+=accepted['accepted']
            return True

    def manual_checkout(self,request):
        """Manual miniapp purchase joins this run: the same courier/GPS loop delivers it.
        Uses commit(): the order exists in memory only after SQLite accepted its rows."""
        with self.lock:
            if self.cancel.is_set() or not self.state['running']:
                raise LookupError('No hay una ejecución de clientes activa.')
            committed=self.commit(lambda engine:engine.manual_checkout(request,datetime.now(timezone.utc)))
            # manual_checkout already validated the UUID; normalise case for the lookup.
            order=self.engine.orders.get(str(UUID(request['order_id'])))
            return {'state':'queued' if committed else 'already_accepted','run_id':self.engine.run_id,
                'order_id':order['id'] if order else None,'amount_minor':order['amount'] if order else None,
                'currency':'EUR'}

    def launch(self):
        self.commit(lambda engine:engine.advance(datetime.now(timezone.utc)))
        self.store.metadata('simulation',self.snapshot())
        self.thread.start()
        if self.state['agent_mode']!='traffic':self.agent_thread.start()
        if self.state['traffic_customers']:self.traffic_thread.start()
        return self.snapshot()

    def stop(self):
        self.cancel.set();self.thread.join(3)
        # An already-running HTTP inference may complete later; its result is discarded.
        if self.agent_thread.ident is not None:self.agent_thread.join(.1)
        if self.traffic_thread.ident is not None:self.traffic_thread.join(2)
        return self.snapshot()

    def run(self):
        deadline=time.monotonic();previous=None
        try:
            while not self.cancel.is_set():
                now=None
                def tick(engine):
                    nonlocal now
                    # Sample after acquiring the domain lock. A checkout may
                    # have committed while GPS was waiting; an older clock
                    # would otherwise assign it before its creation time.
                    now=datetime.now(timezone.utc)
                    return engine.advance(now)
                if not self.commit(tick):break
                with self.lock:
                    self.state['ticks']+=1;self.state['last_tick_at']=iso(now)
                    self.state['observed_interval_seconds']=None if previous is None else round((now-previous).total_seconds(),3)
                previous=now;deadline=max(deadline+self.state['interval_seconds'],time.monotonic())
                self.cancel.wait(max(0,deadline-time.monotonic()))
        except Exception:
            logging.exception('Customer GPS worker stopped')
            with self.lock:self.state['error']='La ingesta no pudo continuar. Comprueba la cola y reinicia la demo.'
        finally:
            self.cancel.set()
            with self.lock:self.state.update(running=False,state='stopped' if not self.state['error'] else 'error')
            self.store.metadata('simulation',self.snapshot())

    def agent_loop(self):
        cursor=0;failures=0
        while not self.cancel.is_set():
            with self.lock:
                ids=[cid for cid,c in self.engine.customers.items() if c['decision_mode']!='traffic'];now=datetime.now(timezone.utc)
                cid=ids[cursor%len(ids)];cursor+=1;context=self.engine.context(cid,now)
                if self.state['model_calls']>=self.state['max_model_calls'] and self.decider.mode=='ollama':
                    self.state['agent_state']='limit_reached';return
            if context:
                try:
                    if self.decider.mode=='ollama':
                        with self.lock:self.state['model_calls']+=1
                    decision=self.decider.choose(context)
                    if self.cancel.is_set():return
                    committed=self.commit(lambda engine:engine.decide(cid,context['revision'],decision,datetime.now(timezone.utc)))
                    with self.lock:self.state['decisions']+=int(committed);self.state['agent_error']=None
                    failures=0
                except Exception:
                    failures+=1
                    with self.lock:self.state['agent_error']='Una decisión no pudo ejecutarse. Se reintentará; no se creó una compra inválida.'
                    if failures>=3:
                        with self.lock:self.state['agent_state']='error'
                        return
                    self.cancel.wait(2)
            self.cancel.wait(.5 if self.decider.mode=='ollama' else .3)

    def traffic_batch(self,engine,now):
        rows=[];count=0
        for cid,c in engine.customers.items():
            if c['decision_mode']!='traffic' or c['traffic_next_at']>now:continue
            context=engine.context(cid,now)
            if not context:continue
            rows.extend(engine.decide(cid,context['revision'],self.traffic.choose(context),now))
            # Stagger sessions and actions; clients progress concurrently without
            # 200 threads or a deepcopy/SQLite transaction for every single click.
            rng=random.Random(f"{engine.seed}:{cid}:{c['revision']}:pace")
            c['traffic_next_at']=now+timedelta(seconds=rng.uniform(1.2,3.8))
            count+=1
        return rows,count

    def traffic_loop(self):
        try:
            while not self.cancel.is_set():
                count=0
                def operation(engine):
                    nonlocal count
                    rows,count=self.traffic_batch(engine,datetime.now(timezone.utc))
                    return rows
                try:
                    if self.commit(operation):
                        with self.lock:
                            self.state['traffic_decisions']+=count;self.state['decisions']+=count
                            self.state['traffic_state']='running'
                except Full:
                    # The failed copy is discarded. Retry later with the same
                    # identities and cart state; never invent a published purchase.
                    with self.lock:self.state['traffic_state']='backpressure'
                    self.cancel.wait(2)
                self.cancel.wait(.5)
        except Exception:
            logging.exception('Customer traffic worker stopped')
            with self.lock:self.state['traffic_state']='error'
        finally:
            with self.lock:
                if self.cancel.is_set():self.state['traffic_state']='stopped'
