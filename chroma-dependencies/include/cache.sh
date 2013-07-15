CACHE="${CACHE:-$(pwd)}"
mkdir -p "$CACHE"

file_valid() {
    local file="$1"
    local type="$2"


    if [ ! -s "$file" ]; then
        return 1
    fi
    if [ -n "$type" ]; then
        file_type=$(file $file)
        file_type=${file_type##*: }
        if [[ $file_type != $type* ]]; then
            return 1
        fi
    fi

    return 0

}

cache_get() {
    local location="$1"
    local type="$2"

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
    cp "$entry" .

    # indicate freshness of the entry
    touch "$entry"

    return 0

}
