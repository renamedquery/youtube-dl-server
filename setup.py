#import statements
import json

#save the details to a config file
configFileData = {
    'application_name':str(input('What would you like your youtube-dl-server application to be named? '))
}

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