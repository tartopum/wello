from contextlib import contextmanager

import sqlalchemy
from sqlalchemy_defaults import make_lazy_configured

from . import config
from .config import Config
from . import cuboid_tank
from .cuboid_tank import CuboidTank
from . import cylinder_tank
from .cylinder_tank import CylinderTank
from .shared import Session, request
from . import pump_in_state
from . import tank
from . import urban_network_state
from . import water_flow_in
from . import water_flow_out
from . import water_volume

make_lazy_configured(sqlalchemy.orm.mapper)


@contextmanager
def open_session():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


@request
def save(*args, session=None):
    for obj in args:
        session.add(obj)
