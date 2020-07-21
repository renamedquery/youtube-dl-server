# youtube-dl-server

#### (A modified version of [manbearwiz's youtube-dl-server](https://github.com/manbearwiz/youtube-dl-server). This project is still in the pre-relase stages, so deploy it at your own risk.)

#### What is new in this version?

- You can now specify where to download the videos on the server you are downloading to, which helps simplifiy adding videos to media servers such as Plex or Jellyfin.
- Built in metadata tagging. The downloader will now apply the appropriate metadata to media you download (artist/author/title) so that you dont need to deal with tagging everything once its downloaded. This also helps simplify adding videos to media servers.
- All of the files are hosted locally. Previously, youtube-dl-server reached out to CDNs on the internet for web assets, however this new version has everything included locally. This means that you don't need to be reliant on external CDNs and you are in full control of your files.
- This new version has error pages. The old version had no error pages, which can lead to some user confusion in the instance of a server side error.
- /q has been renamed to /queue so that users know what page they are at, instead of being confused by what "q" means.
- A download progess page where you can view the status of pending, current, past, and failed downloads (the history page at /history).

#### What is coming?

- Local user accounts. The old version did have authentication, however it was hidden. This program is going to be fully authenticated so that you can lock down who is using your server for downloading videos. This will prevent unwanted access to the server.
- You will be able to "subscribe" to YouTube playlists and channels. This feature makes the server auto-download new videos when they are deteced in the playlist/channel. This feature can be very useful for archiving content, such as archiving a channel's videos automatically.
- Docker images (planning on supporting Raspis).
- The ability to administrate the program via Systemctl.
- Detailed error messages.
- Support for downloading videos with captions.
- Support for using multiple proxies for multiple download workers/pollers.

#### How do I set this up?

Setup instructions will be released when the program is in its first release stage. For now, too much can change, so giving instructions right now would be pointless. At the moment, the only packages you need are `ffmpeg` and `python3` (3.6+). This has only been tested on Ubuntu 18.04 and Ubuntu Server 18.04 at the moment, and it may behave differently on other Linux operating systems. Support for Windows and Mac is not a priority, since this is a server application, however the web client works perfectly on all OSes with modern browsers.