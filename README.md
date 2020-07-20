this is a temporary readme, maybe dont readme yet.

advantages:
    can work fully offline:
        original webpage had:
            <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js" integrity="sha384-ZMP7rVo3mIykV+2+9J3UJ46jBk0WLaUAdn689aCwoqbBJiSnjAK/l8WvCWPIPm49" crossorigin="anonymous"></script>
            <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js" integrity="sha384-ChfqqxuZUCnJSK3+MXmPNIyE6ZbWh2IMqE241rYiqJxyMiZ6OW/JmZQ5stwEULTy" crossorigin="anonymous"></script>
            which means that it wouldnt work offline
        now the current one has everything locally stored
        show example of firefox network tab with the old version and the new version showing how the new version is only localhost as opposed to the old one being internet based
    better path names:
        /q has been changed to /queue to avoid confusion on what the heck q means
    error handling:
        the original program would allow you to download a video from the url "" (just an empty url) which leads to errors, the new version checks that the url is valid and if it isnt it sends you to an error page
    updating:
        instead of updating at the users will, the program updates every time a new video is downloaded, to prevent errors due to not updating. this may have certain downsides, but i have not yet identified those

todo:
    add a way to specify which directory the video will download to
    add authentication via google authenticator
    make it so that youtube-dl updates every time the user downloads a video
    add support for multiple google auth keys
    add a webpage for the user to view the progress and history of the downloads, using statuses like PENDING, DOWNLOADING, and FAILED