from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from nose.tools import (assert_equal, assert_is_none,
                        assert_is_not_none, assert_true)
import pytest

from taxi.routing import application
from trips.models import Trip


TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


@database_sync_to_async
def create_user(
        *,
        username='rider@dev.com',
        password='pAssw0rd!',
        group='rider'
):
    # Create user
    user = get_user_model().objects.create_user(
        username=username,
        password=password
    )
    # Create user group
    user_group, _ = Group.objects.get_or_create(name=group)
    user.groups.add(user_group)
    user.save()
    return user


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
class TestWebsockets:

    async def test_authorized_user_can_connect(self, settings):
        # User in-memory channel layers for testing.
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS

        user = await create_user(
            username='rider@example.com',
            group='rider'
        )

        communicator = await auth_connect(user)
        await communicator.disconnect()

    async def auth_connect(user):
        # Force authentication to get sessionID
        client = Client()
        client.force_login(user=user)

        # Pass sessionID in headers to authenticate
        communicator = WebsocketCommunicator(
            application=application,
            path='/taxi/',
            headers=[(
                b'cookie',
                f'sessionid={client.cookies["sessionid"].value}'.encode('ascii')
            )]
        )
        connected, _ = await communicator.connect()
        assert_true(connected)
        return communicator
