# krita_csv_import_export
UPDATE: CSV support was added back so this is not necessary anymore.

Python plugin for Krita to add back CSV support since this is currently broken and removed from the application as of 4.2.9. Probably easier to troubleshoot file format issues from a plugin than from the compiled app.

Actually, importing doesn't work since the Krita API doesn't allow access to animations. I think its possible by creating temp files and importing the animations that way?
