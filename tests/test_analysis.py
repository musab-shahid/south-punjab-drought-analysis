import ast
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'scripts/analysis.py').read_text(encoding='utf-8'))
definitions=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'extract_run_events','assign_rabi_harvest_year'}],type_ignores=[])
ns={'np':np,'pd':pd}
exec(compile(definitions,'analysis_functions','exec'),ns)

class AnalysisTests(unittest.TestCase):
    def events(self,values):
        return ns['extract_run_events'](pd.DataFrame({'date':pd.date_range('2001-01-01',periods=len(values),freq='MS'),'z':values}),'z')
    def test_gap_adds_duration_but_no_severity(self):
        e=self.events([-2.,0.,-1.5]).iloc[0]
        self.assertEqual(e.duration_months,3)
        self.assertEqual(e.cumulative_severity,1.5)
    def test_nan_breaks_and_final_event_closes(self):
        e=self.events([-2.,-2.,np.nan,-1.5,-1.5])
        self.assertEqual(e.duration_months.tolist(),[2,2])
        self.assertEqual(e.cumulative_severity.tolist(),[2.,1.])
    def test_rabi_harvest_year(self):
        p=pd.DataFrame({'year':[2022,2022,2023,2023],'month':[11,12,1,4]})
        self.assertEqual(ns['assign_rabi_harvest_year'](p).rabi_harvest_year.tolist(),[2023]*4)
    def test_release_season_eligibility(self):
        p=pd.read_csv(ROOT/'data/outputs/wheat_drought_validation_panel.csv')
        self.assertEqual(len(p),264)
        self.assertTrue((p.n_months>=5).all())
        self.assertFalse(p.duplicated(['district','harvest_year']).any())
        self.assertEqual(set(p.harvest_year),set(range(2002,2026)))
if __name__=='__main__':unittest.main()
