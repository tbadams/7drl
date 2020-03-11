pyinstaller -F --add-data assets:assets --hidden-import=pkg_resources.py2_warn gid.py
