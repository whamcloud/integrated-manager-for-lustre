#
# ==============================
# Copyright 2011 Whamcloud, Inc.
# ==============================

from chroma_core.models import ManagedOst, ManagedMdt, ManagedMgs, VolumeNode, ManagedHost


class FuzzyLookupFailed(Exception):
    pass


class FuzzyLookupException(Exception):
    pass


def target_vol_id(fuzzy_id):
    try:
        if ":" in fuzzy_id:  # fqdn:/path/to/device
            hostname, device_path = fuzzy_id.split(":")
            # TODO: try other ways to get the host
            mh = ManagedHost.objects.get(fqdn=hostname)
            ln = VolumeNode.objects.get(host=mh,
                                     path=device_path)

            return ln.volume.pk
    except ManagedHost.DoesNotExist:
        raise FuzzyLookupException("Unable to parse host from %s" % fuzzy_id)
    except VolumeNode.DoesNotExist:
        raise FuzzyLookupException("Unable to parse volume from %s" % fuzzy_id)

    raise FuzzyLookupFailed("Unable to resolve '%s'" % fuzzy_id)


def target_vol_data(fuzzy_id):
    if "," and ":" in fuzzy_id:  # primary:/path/to/dev[,failover:/path/to/dev,failover...]
        node_vols = fuzzy_id.split(",")
    elif ":" in fuzzy_id:
        node_vols = [fuzzy_id]
    else:
        raise FuzzyLookupFailed("Unable to resolve '%s'" % fuzzy_id)

    primary = None
    failover_list = []
    lun_id = None
    for node_vol in node_vols:
        try:
            host, device_path = node_vol.split(":")
        except ValueError:
            raise FuzzyLookupException("Malformed volume string '%s'" % node_vol)

        target_lun_pk = target_vol_id("%s:%s" % (host, device_path))

        if lun_id and lun_id != target_lun_pk:
            raise FuzzyLookupException("%s on %s has a different LUN id (%s != %s)" % (device_path, host, target_lun_pk, lun_id))
        elif lun_id == None:
            lun_id = target_lun_pk

        if primary:
            failover_list.append(host)
        else:
            primary = host

    return (primary, failover_list, lun_id)


def mgt_vol_id(fuzzy_id):
    try:
        return target_vol_id(fuzzy_id)
    except FuzzyLookupFailed:
        try:
            # fqdn by itself -- only makes sense for MGS/MGT
            mgs = ManagedMgs.objects.get(managedtargetmount__host__fqdn=fuzzy_id)
            return mgs.volume.pk
        except ManagedMgs.DoesNotExist:
            # maybe they've supplied the MGS id?
            try:
                mgs = ManagedMgs.objects.get(pk=fuzzy_id)
                return mgs.volume.pk
            except (ValueError, ManagedMgs.DoesNotExist):
                raise FuzzyLookupFailed("No MGS volume found on %s" % fuzzy_id)


def mdt_vol_id(fuzzy_id):
    try:
        return target_vol_id(fuzzy_id)
    except FuzzyLookupFailed:
        try:
            mdt = ManagedMdt.objects.get(pk=fuzzy_id)
            return mdt.volume.pk
        except (ValueError, ManagedMdt.DoesNotExist):
            raise FuzzyLookupFailed("No MDT volume found on %s" % fuzzy_id)


def ost_vol_id(fuzzy_id):
    try:
        return target_vol_id(fuzzy_id)
    except FuzzyLookupFailed:
        try:
            ost = ManagedOst.objects.get(pk=fuzzy_id)
            return ost.volume.pk
        except (ValueError, ManagedOst.DoesNotExist):
            raise FuzzyLookupFailed("No OST volume found on %s" % fuzzy_id)
