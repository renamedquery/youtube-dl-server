# a module to help out with communication to the database

import sqlite3, logger

class dbhelper:

    dbcur = None # database cursor
    dbconn = None # database connection

    def __init__(self, database_location) -> None:

        dbconn = sqlite3.connect(database_location)
        dbcur = dbconn.cursor()
        logger.log('SUCCESSFULLY CONNECTED TO THE DATABASE. DID NOT VERIFY INTEGRITY OF CONTENTS.')
        return None        
    
    def runQuery(query, queryQuestionMarkTitles) -> list:

        logger.log('EXECUTING QUERY.')
        return dbconn.execute(query, (*queryQuestionMarkTitles)).fetchall()