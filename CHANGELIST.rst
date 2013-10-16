    New in version 0.1.9:

    - Some improvements to README documentation.

    - Better dependency specifications in setup.py.

    New in version 0.1.8:

    - FIXED BUG #26: Error: TypeError('a float is required',)

    - FIXED BUG #25: Transfer Stats

    New in version 0.1.7:

    - FIXED BUG #29: OSError('No such file or directory: h')

    New in version 0.1.6:

    - FIXED BUG #27: Error: TypeError('a float is required',)

    - FIXED BUG #28: Command line arguments are not repeatable: e.g. --filter

    New in version 0.1.5:

    - FEATURE #12: Implement --checksum option.

    - FIXED BUG #22: Modification time is not being set to match the source
      file modification time when used with --times 

    New in version 0.1.4:

    - FIXED: setuptools used in place of distutils, meaning easier installation.

    - FIXED BUG #19: Latin-1 file names are not supported and throw exceptions.

    New in version 0.1.3:

    - FIXED BUG #17 and #18: Does not obey --recursive option anymore.

    - FIXED BUG #16: Error: __init__() takes at least 5 arguments (4 given)

    New in version 0.1.2:

    - FIXED BUG #15: Specifying source and/or destination files results in
      creation of directories where there should be files, on
      the client or server.

    New in version 0.1.1:

    - FIXED BUG #13: Specifying a file to copy instead of a directory does
      nothing.

    - FIXED BUG #14: Attempted install on a 'Python Fresh' machine

    New in version 0.1.0:

    - Traversal of the Google drive is now more reliable and requires less CPU
      and network requests.
     
    - Intermediate directory creation now occurs through a restructure of the
      directory walking code, ensuring directories are provided to the callback.
     
    - Itemized output now occurs without needing to specify the verbose option.

    - Interrupt handling now works, so Ctrl-C will halt the sync and output the
      progress (bytes sent/received) up to the interrupt.

    - Implemented --progress functionality so that upload progress can be
      monitored.

    - FIXED BUG: Syncs one file and crashes with division by zero error.

    - FIXED BUG: Always: Error: String or Integer object expected for key,
      unicode found.
     
    - FIXED BUG: Files get updated that are in Trash and do not get restored.
