#! /usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import subprocess
import tempfile
from datetime import datetime

# Prerequisites & instructions -----------------------------------------------------------------------------------------

# lame, flac and metaflac need to be installed on the system

# Change to the folder  that should be transcoded ...
#     cd "/Volumes/Media/Music/Popular/Action Bronson/[2011] Well-Done"
# and run this script by calling ...
#     python3 /Users/guenther/Development/python3-transcode/transcode.py

# Settings -------------------------------------------------------------------------------------------------------------

cover_art_output_dir = os.sep + os.path.join('Users', 'guenther', 'Downloads', 'iTunes Cover Art')

itunes_import_dir = os.sep + os.path.join('Users', 'guenther', 'Music', 'iTunes', 'iTunes Media',
                                          'Automatically Add to iTunes.localized')

# Logic starts here ----------------------------------------------------------------------------------------------------


class TranscodeDir(object):
    def __init__(self, input_dir):
        # Sanitize passed path
        if input_dir.endswith('/'):
            input_dir = input_dir[:-1]

        # Check if cover output dir already exists, if not create.
        if not os.path.isdir(cover_art_output_dir):
            os.makedirs(cover_art_output_dir)

        for parent, dir_name, file_paths in os.walk(input_dir):
            files_to_transcode = []

            # Copy files now and remember the files to be transcoded in the next step.
            for file_path in file_paths:
                if os.path.basename(file_path).startswith('.'):
                    print('Skipping "%s" ...' % os.path.basename(file_path))
                elif os.path.basename(file_path) == 'folder.jpg':
                    print('Copying "%s" as "%s.jpg" ...' % (os.path.basename(file_path), os.path.basename(input_dir)))
                    shutil.copy(os.path.join(parent, file_path), cover_art_output_dir)
                    os.rename(os.path.join(cover_art_output_dir, 'folder.jpg'),
                              os.path.join(cover_art_output_dir, os.path.basename(input_dir) + '.jpg'))
                elif file_path.endswith('.mp3') or file_path.endswith('.m4a'):
                    print('Copying "%s" ...' % os.path.basename(file_path))
                    shutil.copy(os.path.join(parent, file_path), itunes_import_dir)
                elif file_path.endswith('.flac'):
                    files_to_transcode.append(file_path)
                else:
                    print('Skipping "%s" ...' % os.path.basename(file_path))

            # Create a temporary directory.
            temp_output = os.path.join(tempfile.gettempdir(), 'transcode_%s' % datetime.now().strftime('%Y%m%d%-H%M%S'))
            os.mkdir(temp_output)

            # Transcode files.
            for n, file_path in enumerate(files_to_transcode):
                input_file_path = os.path.join(parent, file_path)
                output_file_path = os.path.join(temp_output, os.path.basename(file_path)[:-5] + '.mp3')

                print('Transcoding file %i/%i ...' % (n + 1, len(files_to_transcode)))

                # Using flac and lame directly, this leads to a file with no tags at all though.
                # Get all relevant tags of the source file beforehand (album art is omitted on purpose).
                tag_artist = self.get_tag(input_file_path, 'ARTIST')
                tag_title = self.get_tag(input_file_path, 'TITLE')
                tag_track_number = self.get_tag(input_file_path, 'TRACKNUMBER')
                tag_album = self.get_tag(input_file_path, 'ALBUM')
                tag_date = self.get_tag(input_file_path, 'DATE')
                tag_genre = self.get_tag(input_file_path, 'GENRE')
                tag_disk = self.get_tag(input_file_path, 'DISCNUMBER')

                # print('%s - %s - %s - %s - %s - %s - %s' %
                # (tag_artist, tag_date, tag_genre, tag_album, tag_disk, tag_track_number, tag_title))

                # # Transcode by streaming flac output into the lame encoder, pass over the tag values to write.
                command = '/usr/local/bin/flac -c -d "%s" |' % input_file_path
                command += ' lame -V0 --add-id3v2 --pad-id3v2 --ignore-tag-errors --ta "%s" --tt "%s"' % \
                           (tag_artist, tag_title)
                command += ' --tn "%s" --tl "%s" --tg "%s" --ty "%s"' % \
                           (tag_track_number, tag_album, tag_genre, tag_date)
                command += ' --tv "TPOS=%s"' % tag_disk
                command += ' - "%s"' % output_file_path
                transcode_file = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                transcode_file.communicate()

                # Move files from temporary directory to iTunes auto import folder.
                shutil.move(output_file_path, itunes_import_dir)

            # Remove temporary directory.
            os.rmdir(temp_output)

        print('Finished')

    def get_tag(self, in_file_path, metaflac_string):
        metaflac_command = '/usr/local/bin/metaflac "%s" --show-tag=%s' % (in_file_path, metaflac_string)
        metaflac_tag = subprocess.Popen(metaflac_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        get_tag_out, get_tag_err = metaflac_tag.communicate()
        return self.transform_tag(get_tag_out.decode('utf-8'), metaflac_string)  # bytes to UTF-8 string

    @staticmethod
    def better_capitalize(string):
        # Just using .title() doesn't work reliably for single letter words (e.g. "I")
        capitalized_string = ' '.join(word.capitalize() for word in string.split())

        # The method above has a weakness capitalizing the first word inside brackets though.
        if '(' in capitalized_string:
            final_tag = []
            for word in capitalized_string.split('('):
                final_tag.append(word[0].upper() + word[1:])
            capitalized_string = '('.join(final_tag)

        return capitalized_string

    def transform_tag(self, tag_string, metaflac_string):
        tag = tag_string.upper().replace('%s=' % metaflac_string.upper(), '')  # remove "tag=" so only value remains
        tag = tag.replace('\n', '')  # no line breaks
        tag = self.better_capitalize(tag)  # reliably capitalize each single word
        return tag


if __name__ == '__main__':
    TranscodeDir(os.getcwd())
