#import statements
import flask, youtube_dl, sqlite3

#make a connection to the database
ATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

#select the data from the subscriptions table
DATABASE_CURSOR.execute('SELECT * FROM subscriptions ORDER BY subscription_id ASC')
databaseRows = DATABASE_CURSOR.fetchall()