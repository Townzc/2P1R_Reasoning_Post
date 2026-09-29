import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from experiments.thursday_probe_v2.resume_resources import ResumeGenerationBudget,RentalBudget,admit_unit

class ResumeResourcesTests(unittest.TestCase):
 def test_generations_reopen_without_reset_or_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ledger.json';b=ResumeGenerationBudget(p);b.reserve('a',8)
   self.assertEqual(ResumeGenerationBudget(p).used,600)
   with self.assertRaises(ValueError):b.reserve('a',8)
   b.reserve('rest',4264)
   with self.assertRaises(ValueError):b.reserve('over',1)
 def test_windows_sum_and_first_of_time_or_money(self):
  with tempfile.TemporaryDirectory() as d,patch('experiments.thursday_probe_v2.resume_resources.time.time',return_value=10000):
   p=Path(d)/'rental.json';b=RentalBudget(p,'1970-01-01T00:00:00+00:00',10.)
   self.assertEqual(b.remaining(now=3600)['remaining_hard_seconds'],19800)
   with self.assertRaises(ValueError):RentalBudget(p,'1970-01-01T00:01:00+00:00',10.)
   b.close('1970-01-01T01:00:00+00:00')
   c=RentalBudget(p,'1970-01-01T02:00:00+00:00',10.)
   self.assertEqual(c.remaining(now=10800)['powered_seconds_used'],7200)
   self.assertEqual(c.remaining(now=10800)['rental_cost_proxy_cny'],20.)
   self.assertEqual(c.remaining(now=10800)['remaining_hard_seconds'],16200)
 def test_only_next_unit_needs_to_fit(self):
  self.assertTrue(admit_unit(1000,100,5,now=800))
  self.assertFalse(admit_unit(1000,250,5,now=800))
  self.assertFalse(admit_unit(1000,100,.5,now=800))

if __name__=='__main__':unittest.main()
