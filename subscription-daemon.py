#import statements
import flask, youtube_dl, sqlite3, json, time, os

#make a connection to the database
DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

#select the data from the subscriptions table
DATABASE_CURSOR.execute('SELECT * FROM subscriptions ORDER BY subscription_id ASC')
databaseRows = DATABASE_CURSOR.fetchall()

#function to download videos (returns the path of the downloaded video) (borrowed from app.py)
def downloadVideo(videoURL, videoFormat, parentDownloadDir) -> str:

    #the youtube-dl temporary file name (just make it a timestamp so that it doesnt overwrite anything)
    tmpFileNameNumber = str(time.time())

    #set up the youtube downloader object
    youtubeDLObject = youtube_dl.YoutubeDL({'format':videoFormat,'outtmpl':'{}/{}.%(ext)s'.format(parentDownloadDir, tmpFileNameNumber),'default_search':'youtube'})

    #download the metadata so that the video can be tagged for usage with streaming servers
    youtubeVideoData = youtubeDLObject.extract_info(videoURL, download = False)
    
    #get the data that is needed (this isnt a nessecary step, but it makes the code easier to work with)
    youtubeVideoMetadataData = {
        'ext':youtubeVideoData['ext'],
        'title':youtubeVideoData['title'],
        'uploader':youtubeVideoData['uploader'],
        'id':youtubeVideoData['id'],
        'playlist':youtubeVideoData['album'],
        'playlist_index':youtubeVideoData['playlist_index'],
    }

    #download the video
    youtubeDLObject.download([videoURL])

    #encode the media file with the data
    os.system('ffmpeg -i "{}/{}.{}" -metadata title="{}" -metadata author="{}" -metadata artist="{}" -c copy "{}/{}.{}" -nostdin -y'.format(
        parentDownloadDir, #download directory
        tmpFileNameNumber, #filename
        youtubeVideoMetadataData['ext'], #extension
        youtubeVideoMetadataData['title'], #metadata title
        youtubeVideoMetadataData['uploader'], #metadata author (for video)
        youtubeVideoMetadataData['uploader'], #metadata artist (for music)
        parentDownloadDir, #download directory
        youtubeVideoMetadataData['title'], #title
        youtubeVideoMetadataData['ext'] #extension
    ))

    #delete the original file
    os.remove('{}/{}.{}'.format(parentDownloadDir, tmpFileNameNumber, youtubeVideoMetadataData['ext']))

    #return the path of the video
    return '{}/{}.{}'.format(parentDownloadDir, youtubeVideoMetadataData['title'], youtubeVideoMetadataData['ext'])

#iterate through the subscriptions
for subscription in databaseRows:

    #big try catch, in case something is wrong with the subscription link
    try:
    
        #get the data about the subscription
        SUBSCRIPTION_ID = subscription[0] #the id of the entry in the database
        SUBSCRIPTION_URL = subscription[1] #the playlist/channel url that the subscription program monitors
        SUBSCRIPTION_FORMAT = subscription[2] #the format that the videos will be downloaded in
        SUBSCRIPTION_DIR = subscription[3] #the directory where the videos will be downloaded to
        alreadyDownloadedVideoList = json.loads(subscription[4]) #the list of already downloaded videos from the playlist

        #get the list of videos from the playlist/channel
        youtubeDLObject = youtube_dl.YoutubeDL({'default_search':'youtube'})
        playlistOrChannelData = youtubeDLObject.extract_info(SUBSCRIPTION_URL, download = False)

        #iterate through the videos in the playlist
        for entry in playlistOrChannelData['entries']:

            #check that the video is already downloaded
            if (entry['webpage_url'] not in alreadyDownloadedVideoList):

                #try to download the video
                try:
            
                    #download the video
                    downloadVideo(entry['webpage_url'], SUBSCRIPTION_FORMAT, SUBSCRIPTION_DIR)

                    #add the video url to the list of downloaded videos
                    alreadyDownloadedVideoList.append(entry['webpage_url'])
                
                #the video wasnt able to be downloaded
                except:

                    #print a warning
                    print('Skipping "{}" in the playlist/channel "{}": error while downloading.'.format(entry['webpage_url'], SUBSCRIPTION_URL))

            
            #the video is already downloaded, just display a message that it already is here
            else:

                #print the message
                print('Skipping "{}" in the playlist/channel "{}": already downloaded.'.format(entry['webpage_url'], SUBSCRIPTION_URL))
            
            #update the downloaded video list
            DATABASE_CONNECTION.execute('UPDATE subscriptions SET downloaded_video_list_json = ? WHERE subscription_id = ?', (json.dumps(alreadyDownloadedVideoList), SUBSCRIPTION_ID))
            DATABASE_CONNECTION.commit()
    
    #something went wrong, print an error
    except:

        #print an error and the information about the playlist
        print('Error with the playlist: {}'.format(subscription))