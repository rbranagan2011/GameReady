from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Profile


class PlayerStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='athlete', password='pw')
        # Profile is auto-created via signal
        self.user.profile.role = Profile.Role.ATHLETE
        self.user.profile.save()

    def test_profile_default_status(self):
        p = self.user.profile
        self.assertEqual(p.current_status, Profile.PlayerStatus.AVAILABLE)

    def test_get_player_status_requires_login(self):
        url = reverse('core:player_status')
        resp = self.client.get(url)
        # redirected to login
        self.assertIn(resp.status_code, (302, 301))

    def test_get_and_set_status(self):
        self.client.login(username='athlete', password='pw')
        # GET
        url = reverse('core:player_status')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])
        # POST set
        set_url = reverse('core:player_set_status')
        r2 = self.client.post(set_url, data={'status': 'INJURED', 'note': 'ankle'}, content_type='application/json')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['current_status'], 'INJURED')

# Create your tests here.
