#!/usr/bin/env python


from gmusicapi import Musicmanager


def authenticate():
    """Make an instance of the api and attempts to authenticate the user.
    Return the authenticated api.
    """

    # We are uploading and then downloading so we want Musicmanager
    api = Musicmanager()

    # Attempt to authenticate and log in
    logged_in = api.login()

    # If login() returns false, you have not performed oauth yet, or did not
    # write your credentials to your disk. Using oauth allows authentication
    # without providing plaintext credentials to the application
    if not logged_in:
        print('No oauth credentials found, please authenticate your account')

        # Performs oauth and stores generated credentials to Appdirs 
        # 'user_data_dir' by default. oauth only needs to be performed once per 
        # machine if the credentials are stored, which is the default behavior.
        authenticated = api.perform_oauth(open_browser=True)
    else:
        print('Successfully logged in.\n')

    return api


def demonstrate():
    """ Demonstrate some api features. """

    api = authenticate()

    # Demonstrate upload feature.
    # Create a list of one or more file paths of the mp3s you would like 
    # to upload
    filepaths = []
    filepaths.append('./song1.mp3')

    # Upload an mp3 to your library. upload() returns a tuple of information
    # about the success or failure of uploads
    print("Beginning upload...\n")
    uploaded = api.upload(filepaths) 

    # Print all successfully uploaded songs
    if len(uploaded[0]) > 0:
        print("Successfully uploaded:")
        i = 1
        for key in uploaded[0]:
            print("%d. %s" % (i, key))
            i += 1

    # Print all unsuccessfully uploaded songs and a description of why
    # songs weren't uploaded
    if len(uploaded[2]) == 0:
        print("\nAll songs successfully uploaded.")
    else:
        print("Not all songs were successfully uploaded:")
        i = 1
        for key in uploaded[2]:
            print("%d. %s not uploaded: %s" % (i, key, uploaded[2][key]))
            i += 1


    # Demonstrate download feature
    # Get information about songs previously uploaded that are available
    # to be downloaded
    uploaded_songs = api.get_uploaded_songs()

    if len(uploaded_songs) == 0:
        print("There are no songs currently available for download")
    else:
        # Print songs that are available for download and store their ids
        # so we can download them
        song_ids = []
        print("\nThe following songs are available for download")
        for i in range(len(uploaded_songs)):
            song_ids.append(uploaded_songs[i]['id'])
            print("%d. %s" % (i+1, uploaded_songs[i]['title']))

        # Download uploaded songs from your library
        print("\nBeginning download...")
        for i in range(len(song_ids)):
            filename, audio = api.download_song(song_ids[i])

            # Write song to disk
            with open(filename, 'wb') as f:
                f.write(audio)

            print("%d. Written to ./%s" % (i + 1, filename))
        print("\nDownload complete.")

    # It's good practice to logout when finished
    api.logout()


if __name__ == '__main__':
    demonstrate()
    