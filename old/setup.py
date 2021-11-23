#import statements
import sqlite3, os, getpass
import werkzeug.security as WZS
import argparse

from config import DATABASE_PATH

def setup():
    #check if there is already a database
    if (os.path.exists(DATABASE_PATH)):

        #tell the user that there is a database, then exit. the user will then do what they need to do with the old database.
        print('There already is an existing database! Please move the old database to another directory, or if you are trying to use the old database again, rename it to "youtube-dl-server-database.db.old", then run the setup program again, and then replace the new database with the old database. Please keep in mind that importing a database from an older version of the program can lead to errors, if its not converted properly!')
        exit()

    parser = argparse.ArgumentParser()
    parser.add_argument("--appname",  type=str, help="name for the application")
    parser.add_argument("--username", type=str, help="username for the admin account")
    parser.add_argument("--password", type=str, help="password for the admin account")
    # Parse arguments from cmdline
    args = parser.parse_args()
    if args.appname and args.username and args.password:
        applicationName = args.appname
        username        = args.username
        password        = args.password
        passwordConfirm = args.password
    #Run the original setup
    else:
        #get the name of the application
        applicationName = str(input('What would you like your youtube-dl-server application to be named? '))

        #get the credentials for the admin user
        print('In order for you to administer the server from the web, there needs to be an admin user. Please create one. Make sure that the admin\'s password is strong.')
        username = str(input('Admin username: '))
        password = str(getpass.getpass(prompt = 'Admin password: '))
        passwordConfirm = str(getpass.getpass(prompt = 'Confirm admin password: '))

    #hash the admins password
    hashedPassword = WZS.generate_password_hash(password)

    #check that the passwords match
    if (not WZS.check_password_hash(hashedPassword, password) or password != passwordConfirm):

        #the passwords didnt match, tell the user that there was an error and then quit
        print('The hashed admin password did not match the plaintext admin password, or the passwords did not match. Please check that the passwords you used match.')
        exit()

    #create the database
    os.mkdir('db') if ('db' not in os.listdir('.')) else print('/db already exists.')
    DATABASE_CONNECTION = sqlite3.connect(DATABASE_PATH)

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
        download_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        title VARCHAR NOT NULL,
        url VARCHAR NOT NULL,
        status INTEGER NOT NULL,
        timestamp INTEGER NOT NULL,
        format VARCHAR NOT NULL,
        download_folder_path VARCHAR NOT NULL,
        actual_download_folder_path VARCHAR NOT NULL,
        proxy VARCHAR NOT NULL,
        rm_date INTEGER NOT NULL,
        title_override VARCHAR NOT NULL,
        author_override VARCHAR NOT NULL
    )
    ''') #find a way to use utc timestamps, just in case, then convert them to local on the front end

    #make the subscriptions table
    DATABASE_CONNECTION.execute('''
    CREATE TABLE subscriptions (
        subscription_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        video_list_url VARCAHR NOT NULL,
        format VARCHAR NOT NULL,
        download_dir VARCHAR NOT NULL,
        downloaded_video_list_json VARCHAR NOT NULL
    )
    ''')

    #the table for the list of download directories
    DATABASE_CONNECTION.execute('''
    CREATE TABLE download_directories (
        dir_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        dir_path VARCHAR NOT NULL
    )
    ''')

    #the table for misc setup information
    DATABASE_CONNECTION.execute('''
    CREATE TABLE app_config (
        config_data_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        config_data_title VARCHAR NOT NULL,
        config_data_content VARCHAR NOT NULL
    )
    ''')

    #the table for the proxies
    DATABASE_CONNECTION.execute('''
    CREATE TABLE proxies (
        proxy_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        proxy_url VARCHAR NOT NULL
    )
    ''')

    #add the application title and default download dir into the database
    DATABASE_CONNECTION.execute('INSERT INTO app_config (config_data_title, config_data_content) VALUES (?, ?)', ('DEFAULT_DOWNLOAD_DIR', './downloads'))
    DATABASE_CONNECTION.execute('INSERT INTO app_config (config_data_title, config_data_content) VALUES (?, ?)', ('APP_TITLE', applicationName))
    DATABASE_CONNECTION.commit()

    #add the admin user to the database
    DATABASE_CONNECTION.execute('INSERT INTO users (username, password, admin) VALUES (?, ?, ?)', (username, hashedPassword, 1)) #1 because admin is either 0 (not admin) or 1 (admin)
    DATABASE_CONNECTION.commit()

    #tell the user information about the config
    print('Setup is complete!')

    #close the database connection
    DATABASE_CONNECTION.close()

if __name__ == "__main__":
    setup()