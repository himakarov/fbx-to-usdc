"""
456.py - runs on Houdini startup for this package.

NOTE: on some builds (observed with Steam Houdini Indie) this stage is too
early for shelf objects to be touched safely, and registration silently does
not take effect. scripts/python/ready.py is the primary, reliable registration
path (deferred via hdefereval, same pattern as the Character Material Tool).
This file is kept as a harmless secondary attempt - registration is
idempotent, so running from both never creates a duplicate button.
"""

try:
    from fbx_to_usdc import shelf_register
    shelf_register.register()
except Exception as _e:
    import sys
    sys.stderr.write("FBX to USDC Converter: shelf registration failed: %s\n" % _e)
