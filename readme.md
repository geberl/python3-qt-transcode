# Installation

Todo

## Requirements

- Python 3
- PyQt5

# Usage

*QtTranscode* can be used both through its graphical user interface and from the command line.

The same `settings.json` is used.

## Via GUI

Todo

## Via Command Line

Note: I cloned this repository into `/Users/guenther/Development/python3-qt-transcode/`. The location on your system will probably differ so adjust the commands accordingly.

Open a Terminal, `cd` into the directory that contains the files you want to transcode & import into iTunes.

    cd Downloads/
    cd "[2017] Dirty Projectors"/

Run the `transcode.py` script using the **Python 3** interpreter of your system.

    python3 /Users/guenther/Development/python3-pt-transcode/transcode.py

Alternatively you can pass a path into the script from any location.

Todo this does not work yet

    python3 /Users/guenther/Development/python3-pt-transcode/transcode.py "/Users/guenther/Downloads/[2017] Dirty Projectors/"

### Creating an alias

For easier use it's a good idea to create a permanent alias to launch the transcode script. This is done by adding the following line to your `/.bash_profile`.

    alias tc='python3 /Users/guenther/Dropbox/dev/tc.py'

Save, quit and re-open the Terminal application.
