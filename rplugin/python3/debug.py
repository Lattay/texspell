# This script is used for debugging purpose
# use it with:
# $ python3 -i ./debug.py
import pynvim
import texspell


def logdef(f):
    print('Defining {}: {}'.format(f.__name__, f.__doc__))
    return f


nvim = None


@logdef
def attach(port):
    '''
    port: path to unix port nvim is listening to
    '''
    global nvim
    nvim = pynvim.attach('socket', path=port)


@logdef
def languagetool():
    '''
    return LanguageTool instance
    '''
    global nvim
    return texspell.backend.LanguageTool('lt', nvim)


port = input('nvim port: ')
attach(port)
lt = languagetool()
