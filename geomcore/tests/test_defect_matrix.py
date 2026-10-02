from __future__ import annotations
import copy, json, math, sys, unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parent; sys.path.insert(0,str(ROOT/'src'))
from validator import validate_ir,error_codes
MANIFEST=json.loads((HERE/'type_manifest.json').read_text(encoding='utf-8'))
CONTRACT=json.loads((HERE/'test_contract.json').read_text(encoding='utf-8'))
KINDS=json.loads((HERE/'data/feature_kinds.json').read_text(encoding='utf-8'))

def primitive(kind,feature):
    common={'id':'p001','kind':kind,'feature':feature,'role':'normal'}
    if kind=='rect': return {**common,'x':100,'y':100,'w':140,'h':64,'rx':6}
    if kind=='circle': return {**common,'cx':180,'cy':150,'r':24}
    if kind=='line': return {**common,'x1':100,'y1':100,'x2':260,'y2':100}
    if kind=='text': return {**common,'x':180,'y':150,'text':'fixture','anchor':'middle','size':10}
    if kind=='polyline': return {**common,'points':[[100,100],[180,100],[180,180],[260,180]]}
    if kind=='polygon': return {**common,'points':[[100,180],[180,80],[260,180]]}
    if kind=='path': return {**common,'d':'M 100 100 H 180 V 180 H 260','fill':False}
    raise KeyError(kind)

def fixture(typ,feat):
    meta=KINDS[typ][feat]
    return {'schema':'geomcore-0.1','type':typ,'variant':meta['variant'],'canvas':{'w':400,'h':300},'primitives':[primitive(meta['kind'],feat)]}

def empty_payload(p):
    k=p['kind']
    if k=='text':p['text']=' ';return 'E_EMPTY_TEXT'
    if k=='rect':p['w']=0;return 'E_NONPOSITIVE_GEOMETRY'
    if k=='circle':p['r']=0;return 'E_NONPOSITIVE_GEOMETRY'
    if k=='line':p['x2'],p['y2']=p['x1'],p['y1'];return 'E_ZERO_LENGTH_LINE'
    if k in ('polyline','polygon'):p['points']=[];return 'E_EMPTY_POINTS'
    if k=='path':p['d']='';return 'E_EMPTY_PATH'

def nonfinite(p):
    k=p['kind']
    if k=='rect':p['x']=float('nan')
    elif k=='circle':p['cx']=float('nan')
    elif k=='line':p['x1']=float('nan')
    elif k=='text':p['x']=float('nan')
    elif k in ('polyline','polygon'):p['points']=[[float('nan'),0],*p['points'][1:]]
    elif k=='path':p['d']='M nan 0 L 1 1'

def oob(p,ir):
    k=p['kind']; w=ir['canvas']['w']
    if k=='rect':p['x']=w+20;return 'E_OUT_OF_BOUNDS'
    if k=='circle':p['cx']=w+20;return 'E_OUT_OF_BOUNDS'
    if k=='line':p['x1']=p['x2']=w+20;return 'E_OUT_OF_BOUNDS'
    if k=='text':p['x']=w+20;return 'E_OUT_OF_BOUNDS'
    if k in ('polyline','polygon'):p['points'][0]=[w+20,20];return 'E_OUT_OF_BOUNDS'
    p['d']='M nan 0 L 1 1';return 'E_NONFINITE'

class EveryElement(unittest.TestCase):
  def test_378_elements_x_8_mutations(self):
    failures=[]; count=0
    for typ,spec in MANIFEST.items():
      for feat in spec['features']:
       for mut in CONTRACT['feature_mutations']:
        count+=1; ir=fixture(typ,feat); expected=set(); caps=None
        if mut=='missing_feature':ir['primitives']=[];expected={'E_REQUIRED_FEATURE_MISSING'}
        elif mut=='empty_payload':expected={empty_payload(ir['primitives'][0])}
        elif mut=='duplicate_id':ir['primitives'].append(copy.deepcopy(ir['primitives'][0]));expected={'E_DUPLICATE_ID'}
        elif mut=='unknown_kind':ir['primitives'][0]['kind']='broken';expected={'E_UNKNOWN_KIND'}
        elif mut=='out_of_bounds':expected={oob(ir['primitives'][0],ir)}
        elif mut=='nonfinite_numeric':nonfinite(ir['primitives'][0]);expected={'E_NONFINITE'}
        elif mut=='feature_overflow':
          for i in range(12):q=copy.deepcopy(ir['primitives'][0]);q['id']=f'p{i+2:03d}';ir['primitives'].append(q)
          caps={feat:8};expected={'E_FEATURE_BUDGET'}
        codes=error_codes(validate_ir(ir,MANIFEST,required_features={feat},per_feature_caps=caps,max_primitives=2048))
        if mut=='positive' and codes:failures.append((typ,feat,mut,sorted(codes)))
        elif mut!='positive' and not expected.issubset(codes):failures.append((typ,feat,mut,sorted(expected),sorted(codes)))
    self.assertEqual(count,3024); self.assertFalse(failures,failures[:20])

  def test_42_types_x_4_stress_cases(self):
    failures=[];count=0
    for typ,spec in MANIFEST.items():
      feat=spec['features'][0]
      for mut in CONTRACT['type_mutations']:
        count+=1; ir=fixture(typ,feat);expected=set()
        if mut=='empty_diagram':ir['primitives']=[];expected={'E_EMPTY_PRIMITIVES'}
        elif mut=='primitive_flood':
          q=ir['primitives'][0]
          for i in range(520):z=copy.deepcopy(q);z['id']=f'f{i}';ir['primitives'].append(z)
          expected={'E_PRIMITIVE_BUDGET'}
        elif mut=='invalid_variant':ir['variant']='__bad__';expected={'E_VARIANT'}
        elif mut=='invalid_canvas':ir['canvas']['w']=0;expected={'E_CANVAS'}
        codes=error_codes(validate_ir(ir,MANIFEST,max_primitives=512))
        if not expected.issubset(codes):failures.append((typ,mut,sorted(expected),sorted(codes)))
    self.assertEqual(count,168);self.assertFalse(failures,failures[:20])

  def test_contract_covers_every_element(self):
    self.assertEqual(len(MANIFEST),42)
    self.assertEqual(sum(len(v['features']) for v in MANIFEST.values()),378)
    self.assertEqual(len(CONTRACT['feature_mutations']),8)
    self.assertEqual(len(CONTRACT['type_mutations']),4)

if __name__=='__main__':unittest.main(verbosity=2)
