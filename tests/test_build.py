import copy
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
import build

class Elements(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.sources=[];self.slides=[];self.image_alts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        if tag=='section' and 'slide' in a.get('class','').split():self.slides.append(a)
        if tag in {'img','script','link'} and ('src' in a or 'href' in a):self.sources.append(a.get('src',a.get('href')))
        if tag=='img':self.image_alts.append(a.get('alt'))

class BuildTests(unittest.TestCase):
    def test_offline_output_and_slide_coverage(self):
        with tempfile.TemporaryDirectory() as d:
            path=build.build(Path(d)/'deck.html');text=path.read_text();doc=Elements();doc.feed(text)
            self.assertEqual(len(doc.slides),12)
            self.assertEqual(len(doc.ids),len(set(doc.ids)))
            self.assertTrue(all(x.startswith('data:') for x in doc.sources))
            self.assertTrue(all(doc.image_alts))
            self.assertNotRegex(text,r'\{\{[A-Z_]+\}\}')
            self.assertNotIn('/home/claude',text)
            self.assertEqual({s['id'] for s in doc.slides},set(build.load_data()['notes']))
    def test_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            first=build.build(Path(d)/'a.html').read_bytes()
            self.assertEqual(first,build.build(Path(d)/'b.html').read_bytes())
    def test_score_validation_and_thresholds(self):
        data=build.load_data()
        for r in data['results']:
            self.assertEqual(r['score']>=30,r['group'] in {'flagged','viral'})
        for score,expected in [(0,'low'),(29,'low'),(30,'medium'),(59,'medium'),(60,'high'),(84,'high'),(85,'critical'),(100,'critical')]:
            self.assertEqual(build.level(score),expected)
        data['results'][0]['score']=101
        with self.assertRaises(ValueError):build.validate_data(data)
    def test_missing_and_duplicate_sample_rows_rejected(self):
        data=build.load_data();data['results'].pop()
        with self.assertRaises(ValueError):build.validate_data(data)
        data=build.load_data();data['results'][1]['repo']=data['results'][0]['repo']
        with self.assertRaises(ValueError):build.validate_data(data)
    def test_config_does_not_inject_markup(self):
        data=build.load_data();data['team_members'][0]['name']='<script>alert(1)</script>'
        fragment=build.fragments(data,build.ROOT)['TEAM_MEMBERS']
        self.assertNotIn('<script>',fragment)
        self.assertIn('&lt;script&gt;',fragment)
    def test_qr_requires_confirmed_url_and_confined_asset(self):
        data=build.load_data();data['qr_asset']='assets/code.png'
        with self.assertRaises(ValueError):build.validate_data(data)
        data['landing_url']='https://example.com';data['qr_asset']='../private.png'
        with self.assertRaises(ValueError):build.qr_block(data,build.ROOT)
    def test_theme_and_traveler_validation(self):
        data=build.load_data();data['appearance']['default_theme']='invalid'
        with self.assertRaises(ValueError):build.validate_data(data)
        data=build.load_data();data['appearance']['traveler']['per_slide']['s4']='unknown'
        with self.assertRaises(ValueError):build.validate_data(data)
    def test_unknown_placeholder_fails(self):
        with self.assertRaises(ValueError):build.substitute('{{UNKNOWN}}',{})

if __name__=='__main__':unittest.main()
