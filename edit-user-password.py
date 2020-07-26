#this script assumes that anybody who has access to the console is an admin

#import statements
import sqlite3, getpass
import werkzeug.security as WZS

#connect to the database
DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

#get the account that they want to change the password for
USERNAME = str(input('What account do you want to change tha password for? '))

#check that the user exists in the database
DATABASE_CURSOR.execute('SELECT * FROM users WHERE username = ?', (USERNAME,))

#check if there is more than 0 rows (user exists)
if (not len(DATABASE_CURSOR.fetchall()) > 0):

    #tell the user that there were no matching users, then quit
    print('No users were found with that username. Exiting.')
    exit()

#get the new password for the account
password = str(getpass.getpass(prompt = 'New password for {}: '.format(USERNAME)))
passwordConfirm = str(getpass.getpass(prompt = 'Confirm new password for {}: '.format(USERNAME)))

#check that the account passwords match
if (password != passwordConfirm):

    #tell the user that the two passwords dont match, then quit
    print('The passwords entered did not match. Exiting.')
    exit()

#update the password
DATABASE_CONNECTION.execute('UPDATE users SET password = ? WHERE username = ?', (WZS.generate_password_hash(password), USERNAME))
DATABASE_CONNECTION.commit()

#tell the user that it was successful
print('Successfully changed account password.')