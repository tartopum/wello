import datetime as dt

from .enum import DigitalOutput

from .. import exceptions, models

MIN_PUMP_RUNNING_DELAY = 5

_min_delay = None  # seconds
_min_flow = None  # mm3/s


def init(min_delay, min_flow):
    global _min_delay, _min_flow

    if min_flow < 0:
        raise ValueError()
    if min_delay <= 0:
        raise ValueError()

    _min_delay, _min_flow = min_delay, min_flow


def check_init(func):
    def wrapper(*args, **kwargs):
        if _min_delay is None or _min_flow is None:
            raise exceptions.NeedInitialisation()

        return func(*args, **kwargs)
    return wrapper


@check_init
def pump_in():
    current_state = models.pump_in_state.last()
    last_stop = models.pump_in_state.last(running=False)
    flow = models.water_flow_in.last()

    if current_state is None or last_stop is None or flow is None:
        return DigitalOutput.any

    now = dt.datetime.utcnow()
    running = current_state.running
    last_stop_date = last_stop.datetime
    flow = flow.flow

    delay = (now - current_state.datetime).total_seconds()

    if running and delay >= MIN_PUMP_RUNNING_DELAY and flow <= _min_flow:  # The well is empty
        return DigitalOutput.off

    delay = (now - last_stop_date).total_seconds()

    if not running and delay >= _min_delay:  # The well has filled
        return DigitalOutput.on

    return DigitalOutput.any


@check_init
def urban_network():
    return DigitalOutput.any
