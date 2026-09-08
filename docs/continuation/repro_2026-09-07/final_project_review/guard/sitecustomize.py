"""Review subprocess isolation: block external sockets and live operational writes."""
import os
from pathlib import Path
import sys

LIVE = os.path.normcase('C:/Users/Superleo13/projetos/brasileirao-predictor')


def protected(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return False
    value = os.path.normcase(str(Path(path).resolve()))
    root = os.path.normcase(str(Path(LIVE).resolve()))
    return value.startswith(root + os.sep) and not value.startswith(root + os.sep + '.venv' + os.sep)


def audit(event, args):
    if event == 'socket.connect':
        address = args[1]
        if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
            raise PermissionError('External network disabled for isolated project validation')
    elif event == 'open':
        path, mode, flags = args
        writing = (mode and any(c in mode for c in 'wax+')) or (flags and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing and protected(path):
            raise PermissionError('Validation cannot write to operational checkout')
    elif event in ('os.remove', 'os.rmdir', 'os.mkdir') and protected(args[0]):
        raise PermissionError('Validation cannot mutate operational checkout')
    elif event == 'os.rename' and any(protected(p) for p in args[:2]):
        raise PermissionError('Validation cannot move operational checkout files')


sys.addaudithook(audit)
