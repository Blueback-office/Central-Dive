from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock
import caldav
from icalendar import Calendar, Event
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class TestCaldavSync(TransactionCase):

    def setUp(self):
        super(TestCaldavSync, self).setUp()
        self.user = self.env["res.users"].create(
            {
                "name": "Test User",
                "login": "testuser",
                "caldav_calendar_url": "http://test.calendar.url",
                "caldav_username": "testuser",
                "caldav_password": "password",
            }
        )
        self.env = self.env(context=dict(self.env.context, no_reset_password=True))

    @patch(
        "odoo.addons.caldav_sync.models.calendar_event.CalendarEvent._get_caldav_client"
    )
    def test_create_caldav_event(self, mock_get_caldav_client):
        mock_client = MagicMock()
        mock_calendar = MagicMock()

        def add_event_side_effect(ical_event):
            caldav_event = MagicMock()
            cal = Calendar.from_ical(ical_event)
            ical_event_instance = next(iter(cal.subcomponents))
            caldav_event.vobject_instance.vevent.uid.value = ical_event_instance["UID"]
            return caldav_event

        mock_calendar.add_event.side_effect = add_event_side_effect
        mock_get_caldav_client.return_value = mock_client
        mock_client.calendar.return_value = mock_calendar

        event_data = {
            "name": "Test Event",
            "start": "2024-05-22 10:00:00",
            "stop": "2024-05-22 11:00:00",
            "description": "This is a test event",
            "location": "Test Location",
        }

        event = self.env["calendar.event"].with_user(self.user).create(event_data)

        cal = Calendar.from_ical(mock_calendar.add_event.call_args[0][0])
        ical_event = next(iter(cal.subcomponents))

        self.assertEqual(str(ical_event.get("summary")), event_data["name"])
        self.assertEqual(str(ical_event.get("location")), event_data["location"])
        self.assertEqual(ical_event.get("description"), event_data["description"])
        self.assertIsNotNone(event.caldav_uid)
        self.assertEqual(event.caldav_uid, ical_event["UID"])

    @patch(
        "odoo.addons.caldav_sync.models.calendar_event.CalendarEvent._get_caldav_client"
    )
    @patch(
        "odoo.addons.caldav_sync.models.calendar_event.CalendarEvent.sync_update_to_caldav"
    )
    def test_update_caldav_event(
        self, mock_sync_update_to_caldav, mock_get_caldav_client
    ):
        mock_client = MagicMock()
        mock_calendar = MagicMock()
        mock_event = MagicMock()
        mock_event.id = "test-uid-12345"

        mock_client.calendar.return_value = mock_calendar
        mock_calendar.add_event.return_value = mock_event
        mock_get_caldav_client.return_value = mock_client

        event = (
            self.env["calendar.event"]
            .with_user(self.user)
            .create(
                {
                    "name": "Test Event",
                    "start": "2024-05-22 10:00:00",
                    "stop": "2024-05-22 11:00:00",
                    "description": "This is a test event",
                    "location": "Test Location",
                    "create_uid": self.user.id,
                }
            )
        )

        event.with_user(self.user).write(
            {
                "name": "Updated Test Event",
                "start": "2024-05-22 12:00:00",
                "stop": "2024-05-22 13:00:00",
            }
        )
        mock_sync_update_to_caldav.assert_called_once()

        self.assertEqual(event.name, "Updated Test Event")
        self.assertEqual(event.start, datetime(2024, 5, 22, 12, 0))

    @patch(
        "odoo.addons.caldav_sync.models.calendar_event.CalendarEvent._get_caldav_client"
    )
    def test_delete_caldav_event(self, mock_get_caldav_client):
        mock_client = MagicMock()
        mock_calendar = MagicMock()
        mock_event = MagicMock()

        mock_client.calendar.return_value = mock_calendar
        mock_calendar.object_by_uid.return_value = mock_event
        mock_get_caldav_client.return_value = mock_client

        event = (
            self.env["calendar.event"]
            .with_user(self.user)
            .create(
                {
                    "name": "Test Event",
                    "start": "2024-05-22 10:00:00",
                    "stop": "2024-05-22 11:00:00",
                    "description": "This is a test event",
                    "location": "Test Location",
                    "create_uid": self.user.id,
                }
            )
        )
        uid = event.caldav_uid
        event.with_user(self.user).unlink()

        mock_calendar.object_by_uid.assert_called_once_with(uid)
        mock_event.delete.assert_called_once()

    @patch(
        "odoo.addons.caldav_sync.models.calendar_event.CalendarEvent.sync_event_from_ical"
    )
    def test_poll_caldav_server(self, mock_sync_event_from_ical):
        mock_sync_event_from_ical.return_value = None
        with patch("caldav.DAVClient") as MockClient:
            mock_client = MockClient.return_value
            mock_calendar = mock_client.calendar.return_value
            mock_event = MagicMock()

            # Create a Calendar object and add an Event to it
            cal = Calendar()
            event = Event()
            event.add("uid", "test-uid-12345")
            event.add("dtstamp", datetime(2024, 5, 22, 10, 0, 0))
            event.add("dtstart", datetime(2024, 5, 22, 10, 0, 0))
            event.add("dtend", datetime(2024, 5, 22, 11, 0, 0))
            event.add("summary", "Polled Event")
            event.add("description", "This event was polled from CalDAV")
            event.add("location", "Polled Location")
            cal.add_component(event)

            # Set the mock event's icalendar_instance to the iCal string
            mock_event.icalendar_instance = Calendar.from_ical(cal.to_ical())
            mock_calendar.events.return_value = [mock_event]

            self.env["calendar.event"].poll_caldav_server()
            mock_sync_event_from_ical.assert_called_once()
