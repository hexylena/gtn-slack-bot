from django.test import TestCase
from api import videolibrary
from api import slack_listeners

class BasicTestCase(TestCase):
    def setUp(self):
        pass

    def test_validate_completed_commands(self):
        bad = [
            'I just /completed Introduction to transcriptomics',
            '\completed https://usegalaxy.eu/u/user/h/history',
            '/<https://usegalaxy.eu/u/user/h/history|completed>',
            'completed',
            '/ completehttps://usegalaxy.eu/u/monem-1177_/h/large-genome-assembly',
        ]

        good = [
            '/completed history'
        ]

        for b in bad:
            m = videolibrary.BAD_COMPLETED.match(b)
            if m is None:
                print(b)
            self.assertNotEqual(m, None)

        for g in good:
            m = videolibrary.BAD_COMPLETED.match(g)
            self.assertEqual(m, None)
