"""ViGenX publishing and auto-publish layer.

Layers:
  * folder_publisher - organize renders into /renders/YYYY-MM-DD/
  * credentials      - per-platform token/cookie store (gitignored)
  * scheduler        - dependency-free background publish scheduler
  * uploaders/       - folder / youtube / instagram / playwright targets
"""
