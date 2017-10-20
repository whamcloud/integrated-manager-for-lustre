#!/usr/bin/python
'''
Inspired by https://www.mattlayman.com/2015/i18n.html
'''

APP_NAME = 'cluster_sim'

verbose =  __name__ == '__main__'

import locale

# >>> [x for x in os.environ if x.startswith('LC_') and x not in dir(locale)]
# ['LC_PAPER',
#  'LC_IDENTIFICATION',
#  'LC_ADDRESS',
#  'LC_TELEPHONE',
#  'LC_MEASUREMENT',
#  'LC_NAME']
#
# I.e. not all LC_* names met in the wild are known to the module!

def_locale = locale.getdefaultlocale()
def_encoding = locale.getpreferredencoding()

known_locales = dict([(lc_name, getattr(locale, lc_name))
                      for lc_name in dir(locale)
                      if lc_name.startswith('LC_')])

import os

if 'LANG' in os.environ:
    locale.setlocale(locale.LC_ALL, os.environ['LANG'])

for e in os.environ:
    if e.startswith('LC_'):
        if verbose:
            print e, '->', os.environ[e], ':',
        r = None
        if e in known_locales: # not all LC_* are known to the module
            r = locale.setlocale(known_locales[e], os.environ[e])
        if verbose:
            print r

localedir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
assert os.path.isdir(localedir)

import gettext

gettext.install(domain=APP_NAME, localedir=localedir, unicode=True)
translate = gettext.translation(domain=APP_NAME,
                                localedir=localedir,
                                fallback=True)
if not translate.output_charset():
    translate.set_output_charset(locale.getlocale(locale.LC_ALL)[1])
translate.install(unicode=True)

# "export":
_ = translate.gettext # uniuversal
__ = translate.ngettext # for plurals

if __name__ == '__main__':
    print locale.getlocale(locale.LC_ALL)
    print 'locale dir =', localedir
    print translate.info()
    print 'charset = ', translate.charset()
    print 'output charset =', translate.output_charset()
    # print translate.info()
    print 'Hello world', '=', _('Hello world')

#vim: set ai et ts=4 sts=4 sw=4 :EOF#
