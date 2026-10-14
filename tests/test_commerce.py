"""Meaningful commerce invariants: checkout linkage, budgets and delivery continuity."""
import copy
import tempfile
import threading
import unittest
import json
from unittest.mock import patch
from io import BytesIO
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from atlas.commerce import CommerceEngine,ZERO
from atlas.customer_agent import PolicyAgent,OllamaAgent,TrafficAgent
from atlas.customer_runtime import CustomerRuntime
from atlas.contract import validate
from atlas.store import Store,Full


def catalog():
    return {'restaurants':[{'restaurant_id':'shop','name':'Casa de prueba','latitude':40.415,'longitude':-3.704}],
        'products':[{'product_id':'meal','restaurant_id':'shop','product_name':'Menú ficticio','price_minor':900}]}


class CommerceTests(unittest.TestCase):
    def setUp(self):
        self.at=datetime.now(timezone.utc)-timedelta(minutes=10)
        self.engine=CommerceEngine(str(uuid4()),self.at,1,2,42,catalog(),'policy')
        self.cid=next(iter(self.engine.customers));self.policy=PolicyAgent()
        self.engine.advance(self.at)

    def checkout(self,cid=None,at=None):
        cid=cid or self.cid;at=at or self.at
        events=[]
        for n in range(5):
            context=self.engine.context(cid,at+timedelta(seconds=n))
            events+=self.engine.decide(cid,context['revision'],self.policy.choose(context),at+timedelta(seconds=n))
        return events

    def test_checkout_links_actual_click_basket_and_created_order(self):
        rows=self.checkout()
        link=next(r for r in rows if r.get('_stream')=='customer_orders')
        click=next(r for r in rows if r.get('event_type')=='order_submitted')
        order=next(r for r in rows if r.get('_stream')=='order_events')
        self.assertEqual(link['checkout_event_id'],click['event_id'])
        self.assertEqual(link['order_id'],click['order_id'])
        self.assertEqual(link['session_id'],click['session_id'])
        self.assertEqual(order['order_id'],link['order_id'])
        self.assertEqual(link['items'],[['meal',1,900]])
        self.assertEqual(link['amount_minor'],order['amount_minor'])
        self.assertEqual(order['courier_id'],ZERO)
        self.assertEqual(len(self.engine.orders),1)

    def test_no_checkout_before_cart_and_no_second_checkout(self):
        context=self.engine.context(self.cid,self.at)
        with self.assertRaises(ValueError):
            copy.deepcopy(self.engine).decide(self.cid,context['revision'],{'action':'checkout','choice':0,'reason':'buy'},self.at)
        self.assertFalse(self.engine.orders)
        old_revision=self.engine.customers[self.cid]['revision']
        self.checkout()
        self.assertEqual(self.engine.decide(self.cid,old_revision,{'action':'checkout','choice':0,'reason':'retry'},self.at+timedelta(seconds=5)),[])
        self.assertEqual(len(self.engine.orders),1)

    def test_hallucinated_option_rejected_and_budget_enforced(self):
        self.engine.decide(self.cid,1,{'action':'search','choice':0,'reason':'search'},self.at)
        c=self.engine.customers[self.cid]
        with self.assertRaises(ValueError):
            copy.deepcopy(self.engine).decide(self.cid,c['revision'],{'action':'open_restaurant','choice':999,'reason':'x'},self.at)
        self.engine.customers[self.cid]['budget']=500
        self.engine.decide(self.cid,c['revision'],{'action':'open_restaurant','choice':0,'reason':'x'},self.at)
        self.assertNotIn('open_product',self.engine.context(self.cid,self.at)['allowed'])

    def test_delivery_has_same_order_and_reuses_courier_without_jump(self):
        self.checkout();oid=next(iter(self.engine.orders))
        second=list(self.engine.customers)[1];self.checkout(second,self.at+timedelta(seconds=5))
        first=self.engine.advance(self.at+timedelta(seconds=10))
        gps=next(r for r in first if r.get('_stream')=='courier_positions')
        self.assertEqual(gps['order_id'],oid)
        self.assertEqual(sum(o['courier_id'] is not None for o in self.engine.orders.values()),1)
        final=self.engine.advance(self.at+timedelta(seconds=110))
        delivered=next(r for r in final if r.get('_stream')=='order_events' and r['status']=='delivered')
        self.assertEqual(delivered['order_id'],oid)
        endpoint=next(iter(self.engine.couriers.values()))['position']
        next_tick=self.engine.advance(self.at+timedelta(seconds=112))
        next_gps=next(r for r in next_tick if r.get('_stream')=='courier_positions')
        self.assertNotEqual(next_gps['order_id'],oid)
        self.assertAlmostEqual(next_gps['latitude'],endpoint[0],places=6)
        self.assertAlmostEqual(next_gps['longitude'],endpoint[1],places=6)

    def test_queue_failure_does_not_commit_domain_state(self):
        class CH:
            def query(self,sql):return catalog()['restaurants' if 'restaurants' in sql else 'products']
        with tempfile.TemporaryDirectory() as path:
            store=Store(path+'/queue.sqlite',max_pending=1)
            runtime=CustomerRuntime(store,CH(),1,2,2,42,'policy')
            with self.assertRaises(Full):runtime.commit(lambda engine:engine.advance(datetime.now(timezone.utc)))
            self.assertEqual(runtime.engine.tick,0)
            self.assertEqual(store.status()['accepted'],0)
            runtime.cancel.set()
            self.assertFalse(runtime.commit(lambda engine:engine.advance(datetime.now(timezone.utc))))

    def test_model_receives_euros_while_domain_keeps_exact_cents(self):
        context=self.engine.context(self.cid,self.at)
        response={'message':{'content':json.dumps({'action':'search','choice':0,'reason':'Buscar cena por 14 EUR'})}}
        with patch('atlas.customer_agent.urlopen',return_value=BytesIO(json.dumps(response).encode())) as provider:
            decision=OllamaAgent().choose(context)
        sent=json.loads(provider.call_args.args[0].data)
        visible=json.loads(sent['messages'][1]['content'])
        self.assertEqual(visible['budget_eur'],'14.00')
        self.assertNotIn('budget_minor',visible)
        self.assertEqual(self.engine.customers[self.cid]['budget'],1400)
        self.assertEqual(decision['action'],'search')

    def test_bulk_traffic_preserves_ai_ownership_and_checkout_links(self):
        class CH:
            def query(self,sql):return catalog()['restaurants' if 'restaurants' in sql else 'products']
        with tempfile.TemporaryDirectory() as path:
            store=Store(path+'/queue.sqlite',max_pending=10000)
            with patch.object(OllamaAgent,'ready',return_value=True):
                runtime=CustomerRuntime(store,CH(),80,200,2,42,'hybrid')
            start=runtime.engine.start
            runtime.commit(lambda engine:engine.advance(start))
            for second in range(1,45):
                def batch(engine):
                    now=start+timedelta(seconds=second)
                    rows=engine.advance(now) if second%2==0 else []
                    return rows+runtime.traffic_batch(engine,now)[0]
                runtime.commit(batch)
            ai=[c for c in runtime.engine.customers.values() if c['decision_mode']=='ollama']
            self.assertEqual(len(ai),3)
            self.assertTrue(all(c['steps']==0 and not c['cart'] for c in ai))
            self.assertGreater(len(runtime.engine.orders),100)
            rows=[json.loads(payload) for _,payload in store.pending(10000)]
            links=[r for r in rows if r.get('_stream')=='customer_orders']
            clicks={r['event_id']:r for r in rows if r.get('event_type')=='order_submitted'}
            self.assertTrue(links)
            for link in links:
                self.assertEqual(link['decision_mode'],'traffic')
                self.assertEqual(clicks[link['checkout_event_id']]['order_id'],link['order_id'])
                self.assertEqual(link['amount_minor'],sum(q*price for _,q,price in link['items']))
            self.assertEqual(len(links),len({r['order_id'] for r in links}))
            runtime.cancel.set()

    def test_gps_waiting_for_checkout_samples_clock_after_commit_lock(self):
        class CH:
            def query(self,sql):return catalog()['restaurants' if 'restaurants' in sql else 'products']
        with tempfile.TemporaryDirectory() as path:
            runtime=CustomerRuntime(Store(path+'/queue.sqlite'),CH(),1,1,2,42,'policy')
            original=runtime.commit
            original(lambda engine:engine.advance(datetime.now(timezone.utc)))
            waiting=threading.Event();proceed=threading.Event()
            def delayed(operation):
                waiting.set()
                if not proceed.wait(3):raise RuntimeError('test synchronization timed out')
                result=original(operation);runtime.cancel.set();return result
            runtime.commit=delayed
            worker=threading.Thread(target=runtime.run);worker.start()
            self.assertTrue(waiting.wait(3))
            cid=next(iter(runtime.engine.customers))
            try:
                for _ in range(5):
                    def step(engine):
                        now=datetime.now(timezone.utc);context=engine.context(cid,now)
                        return engine.decide(cid,context['revision'],PolicyAgent().choose(context),now)
                    original(step)
            finally:
                proceed.set();worker.join(4)
            self.assertFalse(worker.is_alive())
            self.assertIsNone(runtime.state['error'])
            order=next(iter(runtime.engine.orders.values()))
            self.assertGreaterEqual(order['assigned_at'],order['created'])

    def test_legacy_event_payload_not_changed_by_nullable_link(self):
        raw={'schema_version':1,'event_id':str(uuid4()),'session_id':str(uuid4()),'event_time':self.at.isoformat(),
            'event_type':'search','section':'search','city_id':'madrid','source':'old-client','source_kind':'demo_live'}
        normalized=validate(raw)
        self.assertNotIn('order_id',normalized)
        with tempfile.TemporaryDirectory() as path:
            store=Store(path+'/queue.sqlite');store.accept([normalized])
            self.assertEqual(store.accept([validate(raw)])['duplicates'],1)


if __name__=='__main__':unittest.main()
