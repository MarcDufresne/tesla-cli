from unittest.mock import patch, MagicMock

import pytest

from tesla.cli import wait_until_online_or_raise


def test_wake_up(vehicle_mock):
    vehicle_mock.wake_up_retry = 2

    get_vehicle_mock = MagicMock()
    get_vehicle_mock.return_value = vehicle_mock

    with patch("tesla.cli.get_vehicle", get_vehicle_mock):
        wait_until_online_or_raise(vehicle_mock, retry_timeout=0, max_attempts=25)

        vehicle_mock.wake_up_retry = 10
        vehicle_mock.state = "asleep"

        with pytest.raises(Exception):
            wait_until_online_or_raise(vehicle_mock, retry_timeout=0, max_attempts=1)
