"""
pythonrc.py - runs on Houdini startup for this package (alongside 456.py).

Houdini executes scripts/pythonrc.py for every package on its path during
startup. This is a second, more reliable entry point for shelf registration:
if 456.py doesn't fire in a given build/session, this still does. Registration
is idempotent, so running from both is harmless - the button is only created
once.
"""

try:
    from fbx_to_usdc import shelf_register
    shelf_register.register()
except Exception as _e:
    import sys
    sys.stderr.write("FBX to USDC Converter: pythonrc registration failed: %s\n" % _e)
