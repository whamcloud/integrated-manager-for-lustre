
def sizeof_fmt(num):
    # http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size/1094933#1094933
    for x in ['bytes','KB','MB','GB','TB', 'EB', 'ZB', 'YB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

def sizeof_fmt_detailed(num):
    for x in ['','kB','MB','GB','TB', 'EB', 'ZB', 'YB']:
        if num < 1024.0 * 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0

    return int(num)
