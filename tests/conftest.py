from pytest import fixture


class MockVehicle:

    wake_up_retry = 0

    display_name = "Mock"
    state = "asleep"
    vin = "xxxxx"

    def wake_up(self):
        if self.wake_up_retry < 1:
            self.state = "online"
        self.wake_up_retry -= 1


@fixture
def vehicle_mock():
    return MockVehicle()
