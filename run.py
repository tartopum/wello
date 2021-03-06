import wello


def start(config, **kwargs):  # signalslot needs **kwargs
    thread = wello.IOThread()
    thread.start()

    thread = wello.ControllerThread()
    wello.ControllerThread.configure(config)
    thread.start()


if __name__ == '__main__':
    wello.UIThread().start()

    if wello.models.config.is_valid():
        start(wello.models.config.last())
    else:
        # Do not start threads till first configuration
        wello.signals.configuration.connect(start)
