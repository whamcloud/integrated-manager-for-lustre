
def _sanitize_arg(arg):
    if " " in arg:
        arg = '"%s"' % arg

    return arg

def lnet_load():
    return "modprobe lnet"

def lnet_unload():
    return "lustre_rmmod || lctl net down && lustre_rmmod"

def lnet_start():
    return "lctl net up"

def lnet_stop():
    return "lctl net down || (lustre_rmmod; lctl net down)"

def mount(device="", dir=""):
    if len(device) > 0 and len(dir) > 0:
        return "mount -t lustre %s %s" % (device, dir)
    else:
        raise ValueError, "mount() needs both device and dir"

def umount(device="", dir=""):
    if len(device) > 0 and len(dir) > 0:
        return "umount %s || umount %s" % (device, dir)
    elif len(device) > 0:
        return "umount %s" % device
    elif len(dir) > 0:
        return "umount %s" % dir
    else:
        return "umount -a -tlustre"

def mkfs(device="", target_types=(), mgsnode=(), fsname="", failnode=(),
         servicenode=(), param={}, index="", comment="", mountfsoptions="",
         network=(), backfstype="", device_size="", mkfsoptions="",
         reformat=False, stripe_count_hint="", iam_dir=False,
         dryrun=False, verbose=False, quiet=False):

    # freeze a view of the namespace before we start messing with it
    args = locals()
    types = ""
    options = ""

    tuple_options = "target_types mgsnode failnode servicenode network".split()
    for name in tuple_options:
        arg = args[name]
        # ensure that our tuple arguments are always tuples, and not strings
        if not hasattr(arg, "__iter__"):
            arg = (arg,)

        if name == "target_types":
            for type in arg:
                types += "--%s " % type
        else:
            if len(arg) > 0:
                options += "--%s=%s " % (name, ",".join(arg))
                
    flag_options = {
        'dryrun': '--dryrun',
        'reformat': '--reformat',
        'iam_dir': '--iam-dir',
        'verbose': '--verbose',
        'quiet': '--quiet',
    }
    for arg in flag_options:
        if args[arg]:
            options += "%s " % flag_options[arg]

    dict_options = "param".split()
    for name in dict_options:
        arg = args[name]
        for key in arg:
            if arg[key] is not None:
                options += "--%s %s=%s " % (name, key, _sanitize_arg(arg[key]))

    # everything else
    handled = set(flag_options.keys() + tuple_options + dict_options)
    for name in set(args.keys()) - handled:
        if name == "device":
            continue
        value = args[name]
        if value != '':
            options += "--%s=%s " % (name, _sanitize_arg(value))

    # NB: Use $PATH instead of relying on hard-coded paths
    cmd = "mkfs.lustre %s %s %s" % (types, options, device)

    return ' '.join(cmd.split())
