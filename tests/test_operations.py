"""Telemetry integrity: ranges, routing, chronology and deterministic simulation."""
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from atlas.operations import validate_operation
from atlas.simulation import Scenario
from atlas.store import Store, Conflict

class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.run=str(uuid4())
        self.at=datetime.now(timezone.utc)-timedelta(minutes=10)
        self.scenario=Scenario(self.run,self.at,3,42)
        self.gps,self.orders,_=self.scenario.sample(self.at)

    def test_coordinates_and_provenance(self):
        original={k:v for k,v in self.gps[0].items() if k!='_stream'}
        for change in [{'latitude':float('nan')},{'longitude':181},{'source_kind':'demo_live'},
                       {'speed_kmh':-1},{'accuracy_m':True}]:
            with self.assertRaises(ValueError):validate_operation('courier_positions',dict(original,**change))

    def test_order_chronology(self):
        original={k:v for k,v in self.orders[0].items() if k!='_stream'}
        with self.assertRaises(ValueError):
            validate_operation('order_events',dict(original,amount_minor=10.5))
        with self.assertRaises(ValueError):
            validate_operation('order_events',dict(original,order_created_at=(self.at+timedelta(seconds=1)).isoformat()))

    def test_deterministic_scenario_and_change(self):
        second=Scenario(self.run,self.at,3,42)
        self.assertEqual((self.gps,self.orders),second.sample(self.at)[:2])
        later=self.scenario.sample(self.at+timedelta(seconds=12))
        self.assertNotEqual(self.gps[0]['event_id'],later[0][0]['event_id'])
        self.assertEqual(self.gps[0]['courier_id'],later[0][0]['courier_id'])

    def test_mixed_stream_retry_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(directory+'/outbox.sqlite')
            events=self.gps+self.orders
            self.assertEqual(store.accept(events)['accepted'],len(events))
            self.assertEqual(Store(store.path).accept(events)['duplicates'],len(events))
            with self.assertRaises(Conflict):
                store.accept([dict(self.gps[0],latitude=self.gps[0]['latitude']+.01)])
            self.assertEqual(store.status()['pending'],len(events))

    def test_live_shared_connection_and_reopen(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as directory:
            store=Store(directory+'/outbox.sqlite',persistent=True)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results=list(pool.map(lambda _:store.accept(self.gps),range(8)))
            self.assertEqual(sum(r['accepted'] for r in results),len(self.gps))
            store.close()
            restored=Store(store.path)
            self.assertEqual(restored.accept(self.gps)['duplicates'],len(self.gps))

if __name__=='__main__':unittest.main()
