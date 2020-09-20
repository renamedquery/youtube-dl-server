import os
# Check for legacy DB to not break anything
if (os.path.exists('./youtube-dl-server-database.db')):
    DATABASE_PATH = ('./youtube-dl-server-database.db')
else:
    DATABASE_PATH = os.path.join('db' + os.sep + 'youtube-dl-server-database.db')
# LEGACY DATABASE_PATH
#DATABASE_PATH = ('./youtube-dl-server-database.db')