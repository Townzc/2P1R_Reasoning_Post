import unittest
from scripts.diagnose_family_lengths import diagnose,structure_witness,FAMILIES


def rows(lengths=(10,11)):
    return [{'problem_id':'p','family':f,'structure_id':str(i),'ac_class':f+str(i),
             'n_supervised':lengths[j],'expression':f+str(i)} for j,f in enumerate(FAMILIES) for i in range(4)]


class Tests(unittest.TestCase):
    def test_cross_family_length_constraint_is_separate(self):
        result=diagnose(rows(),{'p':{'problem_id':'p','numbers':[1,2,3,4],'target':5}})
        self.assertEqual(result['counts'],{'common_class':0,'common_structure':0,'per_family_class':1,'per_family_structure':1})
    def test_common_length_agrees(self):
        result=diagnose(rows((10,10)),{'p':{'problem_id':'p','numbers':[1,2,3,4],'target':5}})
        self.assertTrue(all(n==1 for n in result['counts'].values()))
    def test_mixed_class_conflict_not_double_counted(self):
        data=rows()
        for i,r in enumerate(data):r['ac_class']=str(i%4)
        self.assertIsNone(structure_witness(data))
    def test_different_structures_required(self):
        data=rows()
        for r in data:r['structure_id']='one'
        result=diagnose(data,{'p':{'problem_id':'p','numbers':[1,2,3,4],'target':5}})
        self.assertEqual(result['counts']['per_family_class'],1)
        self.assertEqual(result['counts']['per_family_structure'],0)

if __name__=='__main__':unittest.main()
