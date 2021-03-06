import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pylast
from app.gcloudutils.bucket import upload_to_cloud

from app.models import db, Track, Artist, Album, Playlist, Genre

from app.app import create_app
app = create_app()
app.app_context().push()

# from application.lib.sqlalchemy.exc import IntegrityError
# from application.lib.psycopg2 import IntegrityError

# API Credentials go here


def walk_playlist(specific_playlist=None):
    # Just walk the first page of playlists for now (can paginate later for more data)
    if not specific_playlist:
        sp_playlists = sp.featured_playlists()['playlists']['items']
    else:
        sp_playlists = [specific_playlist]
    for i, sp_playlist in enumerate(sp_playlists):
        if confirm(" playlist " + str(i)):
            try:

                print('Playlist: {}/{}'.format(i + 1, len(sp_playlists)))

                # get the full playlist object
                if not specific_playlist:
                    sp_full = sp.user_playlist(
                        'spotify', sp_playlist['id'], fields='tracks, followers')
                else:
                    sp_full = sp_playlist
                playlist = {
                    'name': sp_playlist['name'],
                    'spotify_uri': sp_playlist['uri'],
                    'num_tracks': sp_playlist['tracks']['total'],
                    'num_followers': sp_full['followers']['total'],
                }

                # walk the tracks on the playlist, to get back aggregate data
                playlist_attrs = walk_playlist_tracks(sp_full['tracks'])
                playlist.update(playlist_attrs)

                # create the db playlist obj
                create_playlist(playlist)

                success = False
                while not success:
                    try:
                        db.session.commit()
                    except BaseException as e:
                        print("playlist commit failed\n" + str(e))
                        db.session.rollback()
                    else:
                        success = True

            except Exception as e:
                print(e)
                if hasattr(e, "message"):
                    print(e.message)
                elif hasattr(e, "msg"):
                    print(e.msg)
                else:
                    raise e


def walk_playlist_tracks(sp_tracks):
    attrs = {
        'duration': 0,
        'num_artists': 0,
        'artists': set(),
        'tracks': []
    }

    # paginate all tracks in playlist
    while sp_tracks:
        for i, sp_track in enumerate(sp_tracks['items']):
            print('PTrack: {}/{}'.format(i + 1, len(sp_tracks['items'])))

            sp_track = sp_track['track']

            if db.session.query(Track).filter_by(spotify_uri=sp_track['uri']).first() is not None:
                print("skipping for efficiency")
                attrs['tracks'].append(db.session.query(Track).filter_by(
                    spotify_uri=sp_track['uri']).first())
                continue  # Skip this track, already covered.

            attrs['duration'] += sp_track['duration_ms']

            # create db artist obj from artist ID
            artist = create_artist(sp_track['artists'][0])
            attrs['artists'].add(artist)

            # create db album obj, also get this db track obj
            # from spotify track obj and db artist obj
            album, track = create_album(sp_track, artist)

            attrs['tracks'].append(track)

        sp_tracks = sp.next(sp_tracks) if sp_tracks['next'] else None

    attrs['num_artists'] = len(attrs['artists'])
    attrs['artists'] = list(attrs['artists'])
    return attrs


def create_artist(sp_artist):
    """Creates a db artist obj from a spotify artist obj"""
    sp_artist = sp.artist(sp_artist['id'])
    name = sp_artist['name']
    if len(sp_artist['images']) > 0:
        image_url = upload_to_cloud(sp_artist['images'][0]['url'])
    else:
        image_url = "https://storage.googleapis.com/artifacts.playlistr-front.appspot.com/images/no_image.jpg"
    spotify_uri = sp_artist['uri']
    try:
        lfm_artist = plast.get_artist(name)
        bio = lfm_artist.get_bio_summary()
        playcount = lfm_artist.get_playcount()
    except BaseException as e:
        bio = "N/A"
        playcount = 0

    genres = create_genres(sp_artist['genres'])

    artist = Artist(
        name=name,
        image_url=image_url,
        spotify_uri=spotify_uri,
        bio=bio,
        playcount=playcount)

    # Genres already exist in DB by this point
    for g in sp_artist['genres']:
        # Get genre db obj
        genre = db.session.query(Genre).filter_by(name=g).first()
        artist.genres.append(genre)

    if db.session.query(Artist).filter_by(spotify_uri=artist.spotify_uri).first() is None:
        db.session.add(artist)

    success = False
    while not success:
        try:
            db.session.commit()
        except BaseException as e:
            print("artist commit failed\n" + str(e))
            db.session.rollback()
        else:
            success = True

    return artist


def create_album(sp_track, artist):
    sp_album = sp.album(sp_track['album']['id'])
    name = sp_album['name']
    spotify_uri = sp_album['uri']
    if len(sp_album['images']) > 0:
        image_url = upload_to_cloud(sp_album['images'][0]['url'])
    else:
        image_url = "https://storage.googleapis.com/artifacts.playlistr-front.appspot.com/images/no_image.jpg"
    try:
        lfm_album = plast.get_album(artist.name, name)
        playcount = lfm_album.get_playcount()
        releasedate = lfm_album.get_release_date()
    except BaseException as e:
        playcount = 0
        releasedate = None

    genres = create_genres(sp_album['genres'])

    album = Album(
        name=name,
        spotify_uri=spotify_uri,
        image_url=image_url,
        playcount=playcount,
        releasedate=releasedate,
        artist=artist)

    # Genres already exist in DB by this point
    for g in sp_album['genres']:
        # Get genre db obj
        genre = db.session.query(Genre).filter_by(name=g).first()
        album.genres.append(genre)

    if db.session.query(Album).filter_by(spotify_uri=album.spotify_uri).first() is None:
        db.session.add(album)

    success = False
    while not success:
        try:
            db.session.commit()
        except BaseException as e:
            print("album commit failed\n" + str(e))
            db.session.rollback()
        else:
            success = True

    playlist_track = create_track(sp_track, artist, album)
    sp_tracks = sp_album['tracks']
    walk_tracks(sp_tracks, artist, album, sp_track)

    return album, playlist_track


def walk_tracks(sp_tracks, artist, album, omit_track):
    while sp_tracks:
        for i, sp_track in enumerate(sp_tracks['items']):
            print('\tATrack: {}/{}'.format(i + 1, len(sp_tracks['items'])))
            if sp_track['uri'] != omit_track['uri']:
                create_track(sp.track(sp_track['id']), artist, album)
        sp_tracks = sp.next(sp_tracks) if sp_tracks['next'] else None


def create_track(sp_track, artist, album):
    name = sp_track['name']
    try:
        playcount = plast.get_track(artist.name, name).get_playcount()
    except BaseException as e:
        playcount = 0

    duration = sp_track['duration_ms']
    spotify_uri = sp_track['uri']
    if len(sp_track['album']) > 0:
        image_url = upload_to_cloud(sp_track['album']['images'][0]['url'])
    else:
        image_url = "https://storage.googleapis.com/artifacts.playlistr-front.appspot.com/images/no_image.jpg"
    track = Track(
        name=name,
        playcount=playcount,
        duration=duration,
        spotify_uri=spotify_uri,
        image_url=image_url,
        album=album,
        artist=artist)

    if db.session.query(Track).filter_by(spotify_uri=track.spotify_uri).first() is None:
        db.session.add(track)

    success = False
    while not success:
        try:
            db.session.commit()
        except BaseException as e:
            print(" track commit failed\n" + str(e))
            db.session.rollback()
        else:
            success = True

    return track


def create_playlist(playlist_attrs):
    playlist = Playlist(**playlist_attrs)
    if db.session.query(Playlist).filter_by(spotify_uri=playlist.spotify_uri).first() is None:
        db.session.add(playlist)
    return playlist


def create_genres(genres):
    genres = [Genre(name=g) for g in genres]
    for g in genres:
        try:
            # db.session.begin(nested=True)
            if db.session.query(Genre).filter_by(name=g.name).first() is None:
                print("Adding genre "+g.name)
                db.session.add(g)
                db.session.commit()
            else:
                print("\tExists "+g.name)

        except BaseException as ie:
            print("skipped")
            raise ie
    return genres


def confirm(item):
    """
    Ask user to enter Y or N (case-insensitive).
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input("OK to go to next" + item + "[y/n]? ").lower()
    return answer == "y"


if __name__ == "__main__":
    walk_playlist()
