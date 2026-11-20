"""Run through manage.py shell only in the empty, synthetic ARM64 CI database."""

import base64
import subprocess
import sys

from django.conf import settings
from django.test import Client
from zerver.actions.create_realm import do_create_realm
from zerver.actions.create_user import do_create_user
from zerver.actions.message_send import check_send_private_message
from zerver.models import Client as ZulipClient
from zerver.models import Message, Realm, UserProfile


def move(realm_id, subdomain):
    subprocess.run([
        sys.executable, "manage.py", "change_realm_subdomain", "--realm", str(realm_id),
        "--skip-redirect", subdomain,
    ], check=True)


def main():
    if settings.EXTERNAL_HOST != "chat.example.com" or Realm.objects.exclude(string_id="zulipinternal").exists():
        raise RuntimeError("Organization smoke test requires the empty chat.example.com CI fixture")
    if settings.ROOT_DOMAIN_LANDING_PAGE:
        raise RuntimeError("The fixture must permit the existing root organization")

    root = do_create_realm("", "CI original organization", invite_required=True)
    owner = do_create_user("operator@example.com", None, root, "CI operator",
                           role=UserProfile.ROLE_REALM_OWNER, acting_user=None,
                           realm_creation=True, enable_marketing_emails=False)
    client, _ = ZulipClient.objects.get_or_create(name="ci-migration")
    message_id = check_send_private_message(owner, client, owner, "Private migration fixture")
    original_id = root.id
    original_api_key = owner.api_key

    move(original_id, "openops")
    root.refresh_from_db()
    owner.refresh_from_db()
    assert root.string_id == "openops" and root.id == original_id
    assert owner.realm_id == original_id
    assert Message.objects.get(id=message_id).content == "Private migration fixture"
    assert not Realm.objects.filter(string_id="").exists(), "Rename created a root placeholder"

    # Exercise the documented rollback, then return to the intended final state.
    move(original_id, "")
    root.refresh_from_db()
    assert root.string_id == "" and root.id == original_id
    move(original_id, "openops")

    projects = do_create_realm("projects", "CI personal projects", invite_required=True)
    project_owner = do_create_user("operator@example.com", None, projects, "CI project operator",
                                   role=UserProfile.ROLE_REALM_OWNER, acting_user=None,
                                   realm_creation=True, enable_marketing_emails=False)
    for realm, account in ((root, owner), (projects, project_owner)):
        realm.refresh_from_db()
        host = f"{realm.string_id}.{settings.EXTERNAL_HOST}"
        response = Client().get("/login/", secure=True, HTTP_HOST=host)
        assert response.status_code == 200, f"Organization login failed: {host}"
        # UserProfile.email can be masked; authentication uses delivery_email.
        authentication = base64.b64encode(f"{account.delivery_email}:{account.api_key}".encode()).decode()
        headers = {"HTTP_AUTHORIZATION": f"Basic {authentication}"}
        response = Client().get("/api/v1/users/me", secure=True, HTTP_HOST=host, **headers)
        assert response.status_code == 200, f"Own-organization authentication failed at {host}: HTTP {response.status_code}"
        assert response.json()["user_id"] == account.id
        other_host = f"{'projects' if realm.string_id == 'openops' else 'openops'}.{settings.EXTERNAL_HOST}"
        response = Client().get("/api/v1/users/me", secure=True, HTTP_HOST=other_host, **headers)
        assert response.status_code == 401, f"Wrong-organization request returned HTTP {response.status_code}"
        assert response.json()["msg"] == "Account is not associated with this subdomain"
    assert Message.objects.get(id=message_id).realm_id == original_id
    owner.refresh_from_db()
    assert owner.api_key == original_api_key, "The existing account's API key changed during the move"
    print("Organization smoke passed: rename/rollback, preserved account/message, login and credential isolation.")


main()
