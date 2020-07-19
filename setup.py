#import statements
import pyotp as OTP
import qrcode as QR
import sys, json

#get the name that the user wants to use for the google authenticator title
SECRET_URL_APP_TITLE = str(input('What do you want the application to be called in Google Authenticator? (My YoutubeDL Server, Local YTDL Server, etc...) '))

#generate a new secret key (not the best for security, but its better than leaving the application open to the public)
RANDOM_SECRET_KEY = OTP.random_base32()

#generate a url that can be turned into a qr code for google authenticator
SECRET_URL = OTP.totp.TOTP(RANDOM_SECRET_KEY).provisioning_uri(SECRET_URL_APP_TITLE, issuer_name = 'youtube-dl-server')

#save the details to a config file (maybe find another way to store them than plaintext?)
configFileData = {
    'secret':RANDOM_SECRET_KEY,
    'secret_url':SECRET_URL,
    'application_name':SECRET_URL_APP_TITLE
}

#write the config file
configFile = open('./config.json', 'w')
configFile.write(json.dumps(configFileData))
configFile.close()

#generate a qr code so that the user can scan it to the google authenticator app if they want
QR.make(SECRET_URL).save('./qr.png')

#tell the user information about the config
print('''
Setup is complete!
Your secret key is: {}
You can either register this key with your google account manually, or by using the QR code that was placed in "./qr.png".
'''.format(RANDOM_SECRET_KEY))