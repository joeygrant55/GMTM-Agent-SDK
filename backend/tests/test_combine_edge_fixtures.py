"""Synthetic evaluation integrity; no runtime/provider/database imports."""
import json
from pathlib import Path
import unittest

FIXTURES = Path(__file__).parent / 'fixtures'


class CombineEdgeFixtureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((FIXTURES / 'combine_edge_eval_2026_09_07.json').read_text())
        self.public = json.loads((FIXTURES / self.data['source_fixture']).read_text())

    def test_eight_bounded_cases_and_paired_history(self):
        cases = self.data['cases']
        self.assertTrue(self.data['synthetic'])
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({c['id'] for c in cases}), 8)
        for c in cases:
            self.assertEqual(set(c), {'id', 'context', 'message', 'history', 'rubric'})
            self.assertTrue(c['id'].startswith('edge_'))
            self.assertLess(len(json.dumps(c).encode()), 18000)
            self.assertLessEqual(len(c['message']), 2000)
            self.assertLessEqual(len(c['history']), 12)
            self.assertEqual(len(c['history']) % 2, 0)
            self.assertLessEqual(sum(len(t['content']) for t in c['history']), 12000)
            for i, t in enumerate(c['history']):
                self.assertEqual(t['role'], 'assistant' if i % 2 else 'user')
                self.assertLessEqual(len(t['content']), 2000)
            self.assertTrue(c['rubric']['must_include'])
            self.assertTrue(c['rubric']['hard_fail'])

    def test_public_identity_and_required_field_fidelity(self):
        events = {e['event']['event_id']: e for e in self.public['events']}
        for case in self.data['cases']:
            c = case['context']; event_id = c['selected_event']['event_id']
            tasks = {t['task_id']: t for t in events[event_id]['tasks']}
            self.assertEqual({a['task_id'] for a in c['activities']}, set(tasks))
            for a in c['activities']:
                t = tasks[a['task_id']]
                required = [q['title'] for q in t['questions'] if q['required']]
                self.assertEqual(a['title'], t['title'])
                self.assertEqual(a['event_id'], event_id)
                self.assertEqual(a['required_field_count'], len(required))
                if case['id'] == 'edge_absent_field_metadata_no_inference':
                    self.assertIsNone(a['required_fields'])
                else:
                    self.assertEqual(a['required_fields'], [{'type': q['type'], 'title': q['title']} for q in t['questions'] if q['required']])
                self.assertTrue(set(a['missing_fields']).issubset(required))
                self.assertLessEqual(len(a['description']), 1200)
                self.assertEqual(a['continuation_url'], f'https://gmtm.com/virtuals/{event_id}')
                self.assertFalse({'answers', 'payload', 'athlete_id', 'clerk_id'} & set(a))
            self.assertFalse({'athlete_id', 'clerk_id'} & set(c))
            self.assertEqual(c['athlete_id_status'], 'unknown')

    def test_counts_and_unknown_progress(self):
        unknown = 0
        for case in self.data['cases']:
            c = case['context']
            self.assertEqual(c['counts']['activities'], len(c['activities']))
            if c['personal_progress_available']:
                self.assertEqual(c['counts']['submitted'], sum(a['submission_state'] == 'submitted' for a in c['activities']))
                self.assertEqual(c['counts']['fields_present'], sum(a['evidence_state'] == 'fields_present' for a in c['activities']))
            else:
                unknown += 1
                self.assertIsNone(c['counts']['submitted'])
                self.assertIsNone(c['counts']['fields_present'])
                self.assertTrue(all(a['submission_state'] == 'unavailable' and a['evidence_state'] == 'unknown' and not a['missing_fields'] for a in c['activities']))
        self.assertGreater(unknown, 0)


if __name__ == '__main__':
    unittest.main()
