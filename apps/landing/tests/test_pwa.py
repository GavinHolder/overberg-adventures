from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile


def _make_user():
    User = get_user_model()
    u = User.objects.create_user(username='t@t.com', email='t@t.com', password='x', is_active=True)
    UserProfile.objects.filter(user=u).update(first_name='T', indemnity_accepted=True)
    return u


class BaseTemplateTest(TestCase):
    def test_manifest_and_sw_in_base(self):
        from django.template.loader import render_to_string
        html = render_to_string('base_app.html', {'user': _make_user()}, request=None)
        self.assertIn('manifest.json', html)
        self.assertIn('service-worker.js', html)
