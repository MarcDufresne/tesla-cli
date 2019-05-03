import os
from pathlib import Path
from time import sleep

import click
import tesla_api
import yaml

from tesla.cli_utils import format_distance_unit, format_bool_value, format_duration, print_table, debug_print


_client = None
_vehicle: tesla_api.Vehicle = None
_display_unit = "km"

CONFIG_DIR = os.path.join(str(Path.home()), ".tesla_cli")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")


def get_vehicle(vin: str) -> tesla_api.Vehicle:
    for v in _client.list_vehicles():
        if v.vin == vin:
            return v
    else:
        raise Exception("VIN not found on account")


def wait_until_online_or_raise(vehicle: tesla_api.Vehicle, retry_timeout: int = 3, max_attempts: int = 100):
    vehicle.wake_up()
    state = vehicle.state

    if state != "online":
        for attempt_nb in range(max_attempts):
            click.secho(f"{vehicle.display_name} is {state}, waiting for it to wake up...", fg="blue")
            try:
                if (attempt_nb + 1) % 10 == 0:
                    click.secho("Calling wake up again...", fg="yellow")
                    vehicle.wake_up()
                state = get_vehicle(vehicle.vin).state
                if state != "online":
                    raise Exception("State is not online")
            except Exception as e:
                if attempt_nb >= max_attempts - 1:
                    raise Exception(f"Vehicle Connection Error, {e}")
                sleep(retry_timeout)
                continue
            else:
                break

    click.secho(f"{vehicle.display_name} is {state}!", fg="green")


@click.group()
@click.option('--debug/--no-debug', default=False, help="Show additional info.")
@click.pass_context
def cli(ctx, debug: bool):
    ctx.obj['DEBUG'] = debug

    if ctx.invoked_subcommand == "setup":
        return

    if not os.path.isfile(CONFIG_PATH):
        click.secho("No configuration found, please run 'setup' to create the configuration.", fg="red")
        exit(1)

    try:
        with open(CONFIG_PATH, mode="r") as f:
            credentials = yaml.safe_load(f)
    except Exception:
        click.secho("Configuration is malformed or unreadable, please run 'setup' to correct the situation.", fg="red")
        exit(1)

    global _client
    global _vehicle

    _client = tesla_api.TeslaApiClient(credentials['username'], credentials['password'])
    vehicles = _client.list_vehicles()
    for v in vehicles:
        if v.vin == credentials['vin']:
            _vehicle = v
            break


@cli.command(help="Configure credentials to access your car info.")
def setup():
    os.makedirs(CONFIG_DIR, exist_ok=True)

    click.secho(f"Tesla CLI Tool Setup")
    username = click.prompt("Tesla Username (E-mail)", type=click.STRING)
    password = click.prompt("Tesla Password", hide_input=True, type=click.STRING)

    client = tesla_api.TeslaApiClient(username, password)
    vehicles = []

    try:
        vehicles = client.list_vehicles()
    except tesla_api.AuthenticationError:
        click.secho("Invalid credentials, please try again", fg="red")
        exit(1)
    except Exception:
        click.secho("API Error, please try again", fg="red")
        exit(1)

    if len(vehicles) == 1:
        click.secho(f"Only one vehicle found, the following vehicle will be used:")
        click.secho(f"Name: {vehicles[0].display_name}")
        click.secho(f"VIN:  {vehicles[0].vin}")
        vin_choice = vehicles[0].vin
    else:
        # TODO: Support more than one vehicle?
        vin_choice = vehicles[0].vin

    values = {
        "username": username,
        "password": password,
        "vin": vin_choice
    }

    with open(CONFIG_PATH, mode="w") as f:
        yaml.safe_dump(values, stream=f, sort_keys=False)

    click.secho("Done!", fg="green")


@cli.command(help="Wake up the car.")
@click.option("--retry-delay", default=3,
              help="How long to wait between state checks in seconds.", show_default=True)
@click.option("--max-attempts", default=100, help="How many times to try.", show_default=True)
def wake_up(retry_delay: int, max_attempts: int):
    wait_until_online_or_raise(_vehicle, retry_timeout=retry_delay, max_attempts=max_attempts)


@cli.command(help="Get info about the state of the car.")
@click.pass_context
def car_state(ctx):
    wait_until_online_or_raise(_vehicle)
    car_info = _vehicle.get_state()

    if ctx.obj['DEBUG']:
        debug_print(car_info)

    lines = [
        f"Name:        {car_info['vehicle_name']}",
        f"Car Version: {car_info['car_version']}",
        f"Locked:      {format_bool_value(car_info['locked'], 'Yes', 'No')}",
        f"Odometer:    {format_distance_unit(car_info['odometer'], _display_unit)}",
        f"Sentry Mode: {format_bool_value(car_info['sentry_mode'], 'On', 'Off')}",
    ]

    print_table(lines, title="Car State")


@cli.command(help="Get info about the charge state.")
@click.pass_context
def charge_state(ctx):
    wait_until_online_or_raise(_vehicle)
    charge_info = _vehicle.charge.get_state()

    if ctx.obj['DEBUG']:
        debug_print(charge_info)

    kwh_charge_rate = charge_info['charger_voltage'] * charge_info['charger_actual_current'] / 1000

    lines = [
        f"Battery:               {charge_info['battery_level']}%",
        f"Usable Battery:        {charge_info['usable_battery_level']}%",
        f"Rated Range:           {format_distance_unit(charge_info['battery_range'], _display_unit)}",
        f"Est. Range:            {format_distance_unit(charge_info['est_battery_range'], _display_unit)}",
        f"Charge State:          {charge_info['charging_state']}",
        f"Charge Rate (Range):   {format_distance_unit(charge_info['charge_rate'], _display_unit)}/h",
        f"Charge Rate (Current): {kwh_charge_rate} kWh",
        f"Remaining Time:        {format_duration(charge_info['time_to_full_charge'])}",
    ]

    print_table(lines, title="Charge State")


@cli.command(help="Get info about the climate.")
@click.pass_context
def climate_state(ctx):
    wait_until_online_or_raise(_vehicle)
    climate_info = _vehicle.climate.get_state()

    if ctx.obj['DEBUG']:
        debug_print(climate_info)

    lines = [
        f"Interior Temp:       {climate_info['inside_temp']}C",
        f"Exterior Temp:       {climate_info['outside_temp']}C",
        f"Driver Temp Setting: {climate_info['driver_temp_setting']}C",
        f"Fan Status:          {format_bool_value(climate_info['fan_status'], 'On', 'Off')}",
        f"Climate:             {format_bool_value(climate_info['is_climate_on'], 'On', 'Off')}",
    ]

    print_table(lines, title="Climate State")


@cli.command(help="Start climate.")
def climate_start():
    wait_until_online_or_raise(_vehicle)
    _vehicle.climate.start_climate()
    click.secho("Climate started!", fg="green")


@cli.command(help="Stop climate.")
def climate_stop():
    wait_until_online_or_raise(_vehicle)
    _vehicle.climate.stop_climate()
    click.secho("Climate stopped!", fg="green")


def entry_point():
    cli(obj={})


if __name__ == '__main__':
    entry_point()
