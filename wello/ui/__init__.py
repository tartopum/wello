from functools import wraps

import flask
import flask_socketio

import plotly
from plotly.graph_objs import Scatter, Layout

from .. import controllers, exceptions, models, signals
from . import forms

app = flask.Flask(__name__)
socketio = flask_socketio.SocketIO(app)

try:
    app.config.from_pyfile('flask.cfg')
except FileNotFoundError:
    pass

try:
    app.config.from_envvar('WELLO_FLASK_CONFIG_FILE')
except RuntimeError:
    pass


def need_config(func):
    @wraps(func)  # For Flask
    def wrapper(*args, **kwargs):
        if not models.config.is_valid():
            flask.flash("L'application nécessite d'être configurée.", 'error')
            return flask.redirect(flask.url_for('config'))

        return func(*args, **kwargs)
    return wrapper


@app.route('/')
@need_config
def home():
    volume = models.water_volume.last()
    flow_in = models.water_flow_in.last()
    flow_out = models.water_flow_out.last()
    pump_in_state = models.pump_in_state.last()
    urban_network_state = models.urban_network_state.last()

    return flask.render_template(
        'home.html',
        config=models.config.last(),
        tank=models.config.tank(),
        water_volume=volume.volume if volume is not None else None,
        water_flow_in=flow_in.flow if flow_in is not None else None,
        water_flow_out=flow_out.flow if flow_out is not None else None,
        pump_in_state=pump_in_state.running if pump_in_state is not None else None,
        urban_network_state=urban_network_state.running if urban_network_state is not None else None,
    )


@app.route('/pump_in/<int:running>', methods=['POST'])
@need_config
def pump_in(running):
    try:
        controllers.pump_in(running)
    except exceptions.TankMayOverflow:
        flask.flash('Allumer la pompe peut faire déborder la cuve.', 'error')

    return flask.redirect(flask.url_for('home'))


@app.route('/config', methods=['GET', 'POST'])
def config():
    if flask.request.method == 'POST':
        form = forms.Config(flask.request.form)

        if form.validate():
            config = models.Config()
            form.populate_obj(config)

            models.save(config)

            flask.flash("Configuration réussie.", 'success')
            return flask.redirect(flask.url_for('home'))
    else:
        form = forms.Config(obj=models.config.last())

    return flask.render_template(
        'config.html',
        form=form,
        cuboid_tanks=models.cuboid_tank.all(),
        cylinder_tanks=models.cylinder_tank.all(),
    )


@app.route('/create-cylinder-tank', methods=['GET', 'POST'])
def create_cylinder_tank():
    if flask.request.method == 'POST':
        form = forms.CylinderTank(flask.request.form)

        if form.validate():
            model = models.CylinderTank()
            form.populate_obj(model)

            models.save(model)

            return flask.redirect(flask.url_for('config'))
    else:
        form = forms.CylinderTank()

    return flask.render_template('create_cylinder_tank.html', form=form)


@app.route('/create-cuboid-tank', methods=['GET', 'POST'])
def create_cuboid_tank():
    if flask.request.method == 'POST':
        form = forms.CuboidTank(flask.request.form)

        if form.validate():
            model = models.CuboidTank()
            form.populate_obj(model)

            models.save(model)

            return flask.redirect(flask.url_for('config'))
    else:
        form = forms.CuboidTank()

    return flask.render_template('create_cuboid_tank.html', form=form)


@app.route('/statistics')
def statistics():
    # Flow in
    data = models.water_flow_in.all()
    x = [line.datetime for line in data]
    y = [line.flow / 10**6 for line in data]

    flow_in_plot = plotly.offline.plot({
        "data": [Scatter(x=x, y=y)],
        "layout": Layout(
            title="Input flow",
            xaxis=dict(
                title='Date',
            ),
            yaxis=dict(
                title='Flow (L/s)',
            ),
        )
    }, include_plotlyjs=False, output_type='div', show_link=False,)

    # Tank volume
    data = models.water_volume.all()
    x = [line.datetime for line in data]
    y = [line.volume / 10**6 for line in data]

    tank_volume_plot = plotly.offline.plot({
        "data": [Scatter(x=x, y=y)],
        "layout": Layout(
            title="Tank volume",
            xaxis=dict(
                title='Date',
            ),
            yaxis=dict(
                title='Volume (L)',
            ),
        )
    }, include_plotlyjs=False, output_type='div', show_link=False,)
    
    # Flow out
    data = models.water_flow_out.all()
    x = [line.datetime for line in data]
    y = [line.flow / 10**6 for line in data]

    flow_out_plot = plotly.offline.plot({
        "data": [Scatter(x=x, y=y)],
        "layout": Layout(
            title="Output flow",
            xaxis=dict(
                title='Date',
            ),
            yaxis=dict(
                title='Flow (L/s)',
            ),
        )
    }, include_plotlyjs=False, output_type='div', show_link=False,)

    # Urban network
    data = models.urban_network_state.all()
    x = [line.datetime for line in data]
    y = [int(line.running) for line in data]

    urban_network_plot = plotly.offline.plot({
        "data": [Scatter(
            x=x, y=y,
            mode='lines',
            line=dict(
                shape='hv',
            ),
            fill='tozeroy',
        )],
        "layout": Layout(
            title="Urban network",
            xaxis=dict(
                title='Date',
            ),
            yaxis=dict(
                title='Used',
                tickvals=[0, 1],
            ),
        )
    }, include_plotlyjs=False, output_type='div', show_link=False,)

    return flask.render_template(
        'statistics.html',
        flow_in=flow_in_plot,
        flow_out=flow_out_plot,
        tank_volume=tank_volume_plot,
        urban_network=urban_network_plot,
    )


signals.pump_in_state.connect(
    lambda running, **kwargs: socketio.emit('pump_in_state', {'running': running})
)
signals.urban_network_state.connect(
    lambda running, **kwargs: socketio.emit('urban_network_state', {'running': running})
)
signals.water_volume_updated.connect(
    lambda volume, **kwargs: socketio.emit('water_volume', {'volume': volume})
)
signals.water_flow_in_updated.connect(
    lambda value, **kwargs: socketio.emit('water_flow_in', {'value': value})
)
signals.water_flow_out_updated.connect(
    lambda value, **kwargs: socketio.emit('water_flow_out', {'value': value})
)
