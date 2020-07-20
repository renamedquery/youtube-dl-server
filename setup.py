#import statements
import json

#save the details to a config file (maybe find another way to store them than plaintext?)
configFileData = {
    'application_name':SECRET_URL_APP_TITLE
}

#write the config file
configFile = open('./config.json', 'w')
configFile.write(json.dumps(configFileData))
configFile.close()

#tell the user information about the config
print('''
Setup is complete!
'''.format(RANDOM_SECRET_KEY))