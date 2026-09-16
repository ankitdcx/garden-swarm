import unittest
from tools import reviewer_quality_runtime as r
POLICY={'schema':'GardenReviewerQualityPolicy/v1','runtime_assessment_queue':{'closed_statuses':['ADJUDICATED','REJECTED','SUPERSEDED'],'overdue_after_hours':72,'pending_soft_limit':2,'pending_hard_limit':3,'closed_archive_hash_limit':2}}
class ReviewerQualityRuntimeV2Tests(unittest.TestCase):
 def test_overdue_is_preserved(self):
  state={'reviewer_quality_queue':[{'request_id':'1','response_sha256':'a','status':r.QUALITY_STATUS,'created':0}]}; debt=r.maintain_quality_queue(state,POLICY,now=73*3600); self.assertEqual(state['reviewer_quality_queue'][0]['status'],r.OVERDUE_STATUS); self.assertEqual(debt['overdue'],1)
 def test_closed_archive_bounded(self):
  state={'reviewer_quality_queue':[{'request_id':str(i),'response_sha256':str(i),'status':'ADJUDICATED','created':0} for i in range(4)]}; r.maintain_quality_queue(state,POLICY,now=100); self.assertEqual(state['reviewer_quality_queue'],[]); self.assertEqual(len(state['reviewer_quality_archive']),2)
 def test_hard_limit_blocks_new_convergence(self):
  state={'reviewer_quality_queue':[{'request_id':str(i),'response_sha256':str(i),'status':r.QUALITY_STATUS,'created':100} for i in range(3)]}; self.assertTrue(r.quality_debt_blocks_new_convergence(state,POLICY,now=100))
if __name__=='__main__': unittest.main()
