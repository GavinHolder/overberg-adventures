"""
Management command: seed_site

Runs on every container startup (called from entrypoint.sh).
Idempotently configures:
  - django.contrib.sites Site record (domain + name from env)
  - SocialAuthProvider for Google (client_id + secret from env)

Safe to run multiple times — uses get_or_create and only updates
when env vars are non-empty.
"""

import os

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Seed site domain and OAuth providers from environment variables.'

    def handle(self, *args, **options):
        self._seed_site()
        self._seed_google()

    def _seed_site(self):
        """Set Site domain from SITE_DOMAIN env var (falls back to first ALLOWED_HOSTS entry)."""
        allowed = os.environ.get('ALLOWED_HOSTS', '')
        domain = os.environ.get('SITE_DOMAIN') or (allowed.split(',')[0].strip() if allowed else '')
        if not domain:
            self.stdout.write('seed_site: SITE_DOMAIN not set, skipping.')
            return

        site_id = int(os.environ.get('SITE_ID', 1))
        site, created = Site.objects.get_or_create(pk=site_id)
        if site.domain != domain:
            site.domain = domain
            site.name = os.environ.get('SITE_NAME', domain)
            site.save()
            self.stdout.write(f'seed_site: site domain set to {domain}')
        else:
            self.stdout.write(f'seed_site: site domain already {domain}')

    def _seed_google(self):
        """Create/update Google SocialAuthProvider from GOOGLE_CLIENT_ID + GOOGLE_SECRET env vars."""
        from apps.accounts.models import SocialAuthProvider

        client_id = os.environ.get('GOOGLE_CLIENT_ID', '').strip()
        client_secret = os.environ.get('GOOGLE_SECRET', '').strip()

        if not client_id or not client_secret:
            self.stdout.write('seed_site: GOOGLE_CLIENT_ID/SECRET not set, skipping Google provider.')
            return

        provider, created = SocialAuthProvider.objects.get_or_create(provider='google')
        provider.display_name = 'Google'
        provider.client_id = client_id
        provider.client_secret = client_secret
        provider.enabled = True
        provider.save()

        action = 'created' if created else 'updated'
        self.stdout.write(f'seed_site: Google provider {action} (active={provider.is_active})')
