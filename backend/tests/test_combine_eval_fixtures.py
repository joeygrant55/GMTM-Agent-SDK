"""Offline fixture integrity only: no provider, database, or application imports."""
import json
from pathlib import Path
import unittest

FIXTURES = Path(__file__).parent / 'fixtures'


class CombineEvalFixtureTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((FIXTURES / 'combine_model_eval_2026_09_07.json').read_text())
        self.public = json.loads((FIXTURES / self.data['source_fixture']).read_text())

    def test_six_compact_blindable_cases(self):
        cases = self.data['cases']
        self.assertTrue(self.data['synthetic'])
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({case['id'] for case in cases}), 6)
        for case in cases:
            self.assertLess(len(json.dumps(case).encode()), 18000)
            self.assertEqual(set(case), {'id', 'context', 'message', 'history', 'rubric'})
            self.assertTrue(case['rubric']['must_include'])
            self.assertTrue(case['rubric']['hard_fail'])
            for turn in case['history']:
                self.assertIn(turn['role'], ('user', 'assistant'))
                self.assertEqual(set(turn), {'role', 'content'})

    def test_fields_and_ids_match_public_requirements(self):
        events = {item['event']['event_id']: item for item in self.public['events']}
        for case in self.data['cases']:
            context = case['context']
            event_id = context['selected_event']['event_id']
            public = {task['task_id']: task for task in events[event_id]['tasks']}
            self.assertEqual({a['task_id'] for a in context['activities']}, set(public))
            for activity in context['activities']:
                task = public[activity['task_id']]
                required = [q['title'] for q in task['questions'] if q['required']]
                self.assertEqual(activity['title'], task['title'])
                self.assertEqual(activity['event_id'], event_id)
                self.assertEqual(activity['required_field_count'], len(required))
                self.assertTrue(set(activity['missing_fields']).issubset(required))
                self.assertEqual(activity['continuation_url'], f'https://gmtm.com/virtuals/{event_id}')
                self.assertNotIn('payload', activity)
                self.assertNotIn('answers', activity)
            self.assertNotIn('athlete_id', context)
            self.assertNotIn('clerk_id', context)
            self.assertEqual(context['athlete_id_status'], 'unknown')

    def test_synthetic_progress_is_internally_consistent(self):
        for case in self.data['cases']:
            c = case['context']
            self.assertEqual(c['counts']['activities'], len(c['activities']))
            if c['personal_progress_available']:
                self.assertEqual(c['counts']['submitted'], sum(a['submission_state'] == 'submitted' for a in c['activities']))
                self.assertEqual(c['counts']['fields_present'], sum(a['evidence_state'] == 'fields_present' for a in c['activities']))
            else:
                self.assertIsNone(c['counts']['submitted'])
                self.assertIsNone(c['counts']['fields_present'])
                self.assertTrue(all(a['submission_state'] == 'unavailable' and a['evidence_state'] == 'unknown' for a in c['activities']))


if __name__ == '__main__':
    unittest.main()
