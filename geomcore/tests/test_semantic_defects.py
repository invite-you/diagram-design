from __future__ import annotations
import unittest

def sankey_conserved(nodes, flows):
    incoming={k:0 for k in nodes}; outgoing={k:0 for k in nodes}
    for a,b,v in flows:
        if v <= 0: return False
        outgoing[a]+=v; incoming[b]+=v
    for n,quantity in nodes.items():
        if incoming[n] and incoming[n] != quantity: return False
        if outgoing[n] and outgoing[n] != quantity: return False
    return True

def waterfall_consistent(start, deltas, end):
    return start + sum(deltas) == end

def polar_valid(scale_min, scale_max, values, categories):
    return scale_min == 0 and scale_max > 0 and 4 <= len(categories) <= 8 and len(categories)==len(values) and len(set(categories))==len(categories) and all(0 <= v <= scale_max for v in values)

def sequence_budget(lifelines, messages, fragments, alt_regions, nesting):
    return lifelines <= 5 and messages <= 12 and fragments <= 2 and alt_regions <= 2 and nesting <= 1

class TestIntentionalSemanticDefects(unittest.TestCase):
    def test_sankey_conservation(self):
        self.assertTrue(sankey_conserved({'A':80,'B':60,'X':70,'Y':70,'P':50,'Q':55,'R':35}, [('A','X',50),('A','Y',30),('B','X',20),('B','Y',40),('X','P',50),('X','Q',20),('Y','Q',35),('Y','R',35)]))
        self.assertFalse(sankey_conserved({'A':80,'X':70}, [('A','X',79)]))
        self.assertFalse(sankey_conserved({'A':80,'X':80}, [('A','X',-1)]))

    def test_waterfall_arithmetic(self):
        self.assertTrue(waterfall_consistent(240,[80,-55,35],300))
        self.assertFalse(waterfall_consistent(240,[80,-55,35],301))

    def test_polar_fail_closed(self):
        self.assertTrue(polar_valid(0,100,[10,20,30,40],['A','B','C','D']))
        self.assertFalse(polar_valid(10,100,[10,20,30,40],['A','B','C','D']))
        self.assertFalse(polar_valid(0,100,[10,-1,30,40],['A','B','C','D']))
        self.assertFalse(polar_valid(0,100,[10,20,30],['A','B','C']))
        self.assertFalse(polar_valid(0,100,[10,20,30,40],['A','A','C','D']))

    def test_sequence_overload(self):
        self.assertTrue(sequence_budget(5,12,1,2,1))
        self.assertFalse(sequence_budget(6,12,1,2,1))
        self.assertFalse(sequence_budget(5,13,1,2,1))
        self.assertFalse(sequence_budget(5,12,3,2,1))
        self.assertFalse(sequence_budget(5,12,1,3,1))
        self.assertFalse(sequence_budget(5,12,1,2,2))

if __name__=='__main__': unittest.main(verbosity=2)
