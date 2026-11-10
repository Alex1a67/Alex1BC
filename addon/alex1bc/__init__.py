"""Alex1BC - use your phone as a physical camera controller for Blender."""
__version__ = "0.1.0"


def register():
    from . import controller, ui
    controller.register()
    ui.register()


def unregister():
    from . import controller, ui
    ui.unregister()
    controller.unregister()
