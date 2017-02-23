#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
from datetime import datetime
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QMessageBox
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time


def get_tag(in_file_path, metaflac_string):
    metaflac_command = '/usr/local/bin/metaflac "%s" --show-tag=%s' % (in_file_path, metaflac_string)
    metaflac_tag = subprocess.Popen(metaflac_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    get_tag_out, get_tag_err = metaflac_tag.communicate()
    return transform_tag(get_tag_out.decode('utf-8'), metaflac_string)  # bytes to UTF-8 string


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


def transform_tag(tag_string, metaflac_string):
    tag = tag_string.upper().replace('%s=' % metaflac_string.upper(), '')  # remove "tag=" so only value remains
    tag = tag.replace('\n', '')  # no line breaks
    tag = better_capitalize(tag)  # reliably capitalize each single word
    return tag


class DragDropWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('text/uri-list'):
            self.parent.statusBar().showMessage('Drop now ...')
            e.accept()
        else:
            self.parent.statusBar().showMessage('')
            e.ignore()

    def dragLeaveEvent(self, e):
        self.parent.statusBar().showMessage('')

    def dropEvent(self, e):
        if e.mimeData().text().startswith('file://'):  # TODO does this also work for any mix of file(s) and folder(s)?
            input_dir = e.mimeData().text()[len('file://'):]
            if os.path.isdir(input_dir):
                self.parent.start_transcoding(input_dir)
            else:
                self.parent.statusBar().showMessage('Not a directory')


class DragDropWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_ui()

        # Setup queuing (necessary to get communication to between separate threads going).
        self.queue_gui_to_function = queue.Queue()
        self.queue_function_to_gui = queue.Queue()

        # Are we transcoding in this very moment? Closing frame while transcoding opens a confirmation message box.
        self.active_transcode = False

    def init_ui(self):
        self.setGeometry(100, 100, 200, 200)
        self.setWindowTitle('Transcode')

        button_widget = DragDropWidget(self)
        self.setCentralWidget(button_widget)

        self.statusBar().showMessage('Drop folder here.')

        self.show()

    def closeEvent(self, event):
        if self.active_transcode:
            confirmation_message_box = QMessageBox()
            result = confirmation_message_box.question(self,
                                                       'Confirmation',
                                                       'Are you sure you want to cancel transcoding?',
                                                       QMessageBox.Yes | QMessageBox.No)
            event.ignore()
            if result == QMessageBox.Yes:
                self.queue_gui_to_function.put('Cancel')
        else:
            event.accept()

    def start_transcoding(self, input_dir):
        self.active_transcode = True

        # Launch the function that refreshes the status as well as the actual function that processes the files.
        # thread_0 = threading.Thread(target=self.execute_threaded_function, args=(self.wait_some_time, [input_dir]))
        thread_0 = threading.Thread(target=self.execute_threaded_function, args=(self.transcode, [input_dir]))
        thread_0.daemon = False
        thread_0.start()

    def execute_threaded_function(self, function_to_call, objects_to_process):
        # Function to refresh the status.
        thread_1 = threading.Thread(target=self.refresh_status)
        thread_1.daemon = True
        thread_1.start()

        # Function to process the files / folder.
        thread_2 = threading.Thread(target=function_to_call, args=objects_to_process)
        thread_2.daemon = False
        thread_2.start()

        # Continue once thread_2 (the actual function) finishes.
        thread_2.join()

        self.statusBar().showMessage('Done. Ready for next folder.')
        self.active_transcode = False

    def refresh_status(self):
        while True:
            if not self.queue_function_to_gui.empty():
                current_status = self.queue_function_to_gui.get()
                if current_status == '100%':
                    time.sleep(2)
                    return
                else:
                    self.statusBar().showMessage('%s' % current_status)
            time.sleep(0.5)

    def transcode(self, input_dir):
        # TODO add a debug logger for all the prints in here

        # Settings
        cover_art_output_dir = os.sep + os.path.join('Users', 'guenther', 'Downloads', 'iTunes Cover Art')

        itunes_import_dir = os.sep + os.path.join('Users', 'guenther', 'Music', 'iTunes', 'iTunes Media',
                                                  'Automatically Add to iTunes.localized')

        # print(input_dir)
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
                    pass
                    # print('Skipping "%s" ...' % os.path.basename(file_path))
                elif os.path.basename(file_path) == 'folder.jpg':
                    # print('Copying "%s" as "%s.jpg" ...' % (os.path.basename(file_path), os.path.basename(input_dir)))
                    shutil.copy(os.path.join(parent, file_path), cover_art_output_dir)
                    os.rename(os.path.join(cover_art_output_dir, 'folder.jpg'),
                              os.path.join(cover_art_output_dir, os.path.basename(input_dir) + '.jpg'))
                elif file_path.endswith('.mp3') or file_path.endswith('.m4a'):
                    # print('Copying "%s" ...' % os.path.basename(file_path))
                    shutil.copy(os.path.join(parent, file_path), itunes_import_dir)
                elif file_path.endswith('.flac'):
                    files_to_transcode.append(file_path)
                else:
                    pass
                    # print('Skipping "%s" ...' % os.path.basename(file_path))

            # Create a temporary directory.
            temp_output = os.path.join(tempfile.gettempdir(), 'transcode_%s' % datetime.now().strftime('%Y%m%d%-H%M%S'))
            os.mkdir(temp_output)

            # Transcode files.
            # print(files_to_transcode)
            for n, file_path in enumerate(files_to_transcode):
                # Check if user clicked cancel in the meantime. Exit function if so. Continue otherwise.
                if not self.queue_gui_to_function.empty():
                    if self.queue_gui_to_function.get() == 'Cancel':
                        return

                # Update the status bar.
                self.queue_function_to_gui.put('%.2f%%' % (((n + 1) / len(files_to_transcode)) * 100))

                input_file_path = os.path.join(parent, file_path)
                output_file_path = os.path.join(temp_output, os.path.basename(file_path)[:-5] + '.mp3')

                # print('Transcoding file %i/%i ...' % (n + 1, len(files_to_transcode)))

                # Using flac and lame directly, this leads to a file with no tags at all though.
                # Get all relevant tags of the source file beforehand (album art is omitted on purpose).
                tag_artist = get_tag(input_file_path, 'ARTIST')
                tag_title = get_tag(input_file_path, 'TITLE')
                tag_track_number = get_tag(input_file_path, 'TRACKNUMBER')
                tag_album = get_tag(input_file_path, 'ALBUM')
                tag_date = get_tag(input_file_path, 'DATE')
                tag_genre = get_tag(input_file_path, 'GENRE')
                tag_disk = get_tag(input_file_path, 'DISCNUMBER')

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

                # TODO make use of multiple cores on the processor. Transcode two files at the same time.
                # TODO open in this regard: How to show the percentage.

                # Move files from temporary directory to iTunes auto import folder.
                shutil.move(output_file_path, itunes_import_dir)

            # Remove temporary directory.
            os.rmdir(temp_output)

            # Tell the other thread to also finish.
            self.queue_function_to_gui.put('100%')
            return

    def wait_some_time(self, input_dir):
        print(input_dir)

        # Check if user clicked cancel in the meantime. Exit function if so. Continue otherwise.
        if not self.queue_gui_to_function.empty():
            if self.queue_gui_to_function.get() == 'Cancel':
                return

        self.queue_function_to_gui.put('25%')
        time.sleep(2)

        # Check if user clicked cancel in the meantime. Exit function if so. Continue otherwise.
        if not self.queue_gui_to_function.empty():
            if self.queue_gui_to_function.get() == 'Cancel':
                return

        self.queue_function_to_gui.put('50%')
        time.sleep(2)

        # Check if user clicked cancel in the meantime. Exit function if so. Continue otherwise.
        if not self.queue_gui_to_function.empty():
            if self.queue_gui_to_function.get() == 'Cancel':
                return

        self.queue_function_to_gui.put('75%')
        time.sleep(2)

        # Check if user clicked cancel in the meantime. Exit function if so. Continue otherwise.
        if not self.queue_gui_to_function.empty():
            if self.queue_gui_to_function.get() == 'Cancel':
                return

        # Tell the other thread to also finish.
        self.queue_function_to_gui.put('100%')
        time.sleep(2)
        return


def process_cl_args():
    parser = argparse.ArgumentParser()
    parsed, unparsed = parser.parse_known_args()
    return parsed, unparsed


if __name__ == '__main__':
    if len(sys.argv) > 1:
        parsed_args, unparsed_args = process_cl_args()
    else:
        parsed_args = None
        unparsed_args = []
    qt_args = sys.argv[:1] + unparsed_args

    app = QApplication(qt_args)
    ex = DragDropWindow()
    ex.show()
    exit_code = app.exec_()
    sys.exit(exit_code)
