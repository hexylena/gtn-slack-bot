from django.test import TestCase
from api import videolibrary
from api import slack_listeners

class BasicTestCase(TestCase):
    def setUp(self):
        pass

    def test_validate_urls(self):
        e, f = videolibrary.validateGalaxyURLs("test")
        self.assertEqual(len(e), 0)
        self.assertEqual(len(f), 1)

        e, f = videolibrary.validateGalaxyURLs("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(len(e), 0)
        self.assertEqual(len(f), 2)

        e, f = videolibrary.validateGalaxyURLs("https://youtu.be/dQw4w9WgXcQ")
        self.assertEqual(len(e), 0)
        self.assertEqual(len(f), 2)

        e, f = videolibrary.validateGalaxyURLs("https://example.com")
        self.assertEqual(len(e), 0)
        self.assertEqual(len(f), 1)

        e, f = videolibrary.validateGalaxyURLs("https://usegalaxy.org/u/helena-rasche/h/the-beta-history")
        self.assertEqual(len(e), 0)
        self.assertEqual(len(f), 0)


# class CertTestCase(TestCase):
    # def setUp(self):
        # # Animal.objects.create(name="lion", sound="roar")
        # pass

    # def test_validate_urls(self):
        # def ack(*args, **kwargs):
            # pass
        # def client(*args, **kwargs):
            # pass

        # slack_listeners.JOINED.append('channel_xyz')
        # result = slack_listeners.certify(
            # ack, client
        # )
        # self.assertEqual(len(e), 0)
        # self.assertEqual(len(f), 1)
