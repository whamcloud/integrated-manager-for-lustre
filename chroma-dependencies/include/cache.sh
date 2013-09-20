CACHE="${CACHE:-$(pwd)}"
mkdir -p "$CACHE"

file_valid() {
    local file="$1"
    local typ="$2"


    if [ ! -s "$file" ]; then
        return 1
    fi
    if [ -n "$typ" ]; then
        file_typ=$(file $file)
        file_typ=${file_typ##*: }
        if [[ $file_typ != $typ* ]]; then
            return 1
        fi
    fi

    return 0

}

cache_populate() {
    local sha1sum=
    local typ=
    while getopts "t:s:" flag; do
        case "$flag" in
            t) typ=$OPTARG;;
            s) sha1sum=$OPTARG;;
        esac
    done
    local location=${@:$OPTIND:1}

    local name="${location##*/}"
    local entry="$CACHE/$name"
    local lock="$entry.lock"
    # entry exists already
    if [ -f "$entry" ]; then
        # and is not in the process of being created
        if [ ! -f "$lock" ]; then
            if file_valid "$entry" "$typ"; then
                # so it's all good
                echo "$entry"
                return 0
            else
                # but it's a 0-byte file, so invalid, remove and carry on
                rm -f "$entry"
            fi
        fi
        # still being created, so wait for it to be finished
        # TODO: detect the writer's death
        #       this can be done by watching the progress of growth of the
        #       lockfile since curl is writing it's stderr (i.e. 1 every
        #       second or so) to it
        while [ -f "$lock" ]; do
            sleep 1
        done
        # writer's done
        if [ -f "$entry" ]; then
            # return the entry
            echo "$entry"
            return 0
        fi
    fi

    #
    # entry is not there, create it
    #

    # announce intent to create it so others wait
    touch "$lock"

    # fetch to temporary location to make "appearance" atomic
    local tmp_slot="$entry.tmp"
    if ! curl -f -k -L -o "$tmp_slot" "$location" 2> "$lock" ||
        ! file_valid "$tmp_slot" "$typ"; then
        echo "Failed to fetch $location"
        cat "$lock"
        rm -f "$lock" "$tmp_slot"
        return 1
    fi
    mv -f "$tmp_slot" "$entry"

    # got it, remove the lock so others can read it
    rm -f "$lock"

    # check sha1sum, if provided
    if [ -n "$sha1sum" ]; then
        entry_sha1sum=$(sha1sum $entry | awk '{print $1}')
        if ! [ "$sha1sum" == "$entry_sha1sum" ]; then
            echo "sha1sum mismatch on $entry! (got $entry_sha1sum, expected $sha1sum"
            return 1
        fi
    fi

    # indicate freshness of the entry
    touch "$entry"

    echo "$entry"
    return 0

}

# deprecated
# everything should move to chroma-externals
# this is only being used by the nodejs dependencies, soon to be replaced
cache_get() {
    local sha1sum=
    local type=
    while getopts "t:s:" flag; do
        case "$flag" in
            t) type=$OPTARG;;
            s) sha1sum=$OPTARG;;
        esac
    done
    local location=${@:$OPTIND:1}

    local name="${location##*/}"
    local entry="$CACHE/$name"
    local lock="$entry.lock"
    # entry exists already
    if [ -f "$entry" ]; then
        # and is not in the process of being created
        if [ ! -f "$lock" ]; then
            if file_valid "$entry" "$type"; then
                # so it's all good
                cp "$entry" .
                return 0
            else
                # but it's a 0-byte file, so invalid, remove and carry on
                rm -f "$entry"
            fi
        fi
        # still being created, so wait for it to be finished
        # TODO: detect the writer's death
        #       this can be done by watching the progress of growth of the
        #       lockfile since curl is writing it's stderr (i.e. 1 every
        #       second or so) to it
        while [ -f "$lock" ]; do
            sleep 1
        done
        # writer's done
        if [ -f "$entry" ]; then
            # return the entry
            cp "$entry" .
            return 0
        fi
    fi

    #
    # entry is not there, create it
    #

    # announce intent to create it so others wait
    touch "$lock"

    # fetch to temporary location to make "appearance" atomic
    local tmp_slot="$entry.tmp"
    if ! curl -k -L -o "$tmp_slot" "$location" 2> "$lock" ||
        ! file_valid "$tmp_slot" "$type"; then
        echo "Failed to fetch $location"
        cat "$lock"
        rm -f "$lock" "$tmp_slot"
        exit 1
    fi
    mv -f "$tmp_slot" "$entry"

    # got it, remove the lock so others can read it
    rm -f "$lock"

    # check sha1sum, if provided
    if [ -n "$sha1sum" ]; then
        entry_sha1sum=$(sha1sum $entry | awk '{print $1}')
        if ! [ "$sha1sum" == "$entry_sha1sum" ]; then
            echo "sha1sum mismatch on $entry! (got $entry_sha1sum, expected $sha1sum"
            exit 1
        fi
    fi

    # copy from cache into working directory
    cp "$entry" .

    # indicate freshness of the entry
    touch "$entry"

    return 0

}
