#import statements
import json, sqlite3, os

#save the details to a config file
configFileData = {
    'application_name':str(input('What would you like your youtube-dl-server application to be named? '))
}

#check if there is already a database
if (os.path.exists('./youtube-dl-server-database.db')):

    #tell the user that there is a database, then exit. the user will then do what they need to do with the old database.
    print('There already is an existing database! Please move the old database to another directory, or if you are trying to use the old database again, rename it to "youtube-dl-server-database.db.old", then run the setup program again, and then replace the new database with the old database. Please keep in mind that importing a database from an older version of the program can lead to errors, if its not converted properly!')
    exit()

#create the database
DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')

#make the users table
DATABASE_CONNECTION.execute('''
CREATE TABLE users (
    username VARCHAR NOT NULL PRIMARY KEY,
    password VARCHAR NOT NULL,
    admin BOOL NOT NULL DEFAULT 0
)
''')

#make the download history table (i dont think 8 bit variables will be nessecary for most applications, however if they are nessecary for you, then replace SERIAL with SERIAL8 and INT with INT8)
DATABASE_CONNECTION.execute('''
CREATE TABLE download_history (
    download_id SERIAL NOT NULL PRIMARY KEY,
    url VARCHAR NOT NULL,
    status INT NOT NULL
)
''')

#write the config file
configFile = open('./config.json', 'w')
configFile.write(json.dumps(configFileData))
configFile.close()

#make the download directory file (the file where all of the optional download directories are stored)
downloadDirsFile = open('./download-dirs.txt', 'w')
downloadDirsFile.write('''
#Write the absolute path to the directory that you want users to be able to download videos to, sperated by new lines.
#You can comment out entries by starting the line with a pound sign.
#Paths with spaces are supported.
#If no paths are added in this file, then the user will only be able to download to the downloads folder that comes with this program, instead of being able to download to other directories on the server.
#Example lines:
#/home/greg/videos/
#/data/jellyfin/My Videos/Linus Tech Tips/WAN Show/
#/media/mary/flask-drive-videos/
''')

#tell the user information about the config
print('Setup is complete!')