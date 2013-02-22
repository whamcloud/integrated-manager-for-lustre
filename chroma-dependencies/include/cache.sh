CACHE="${CACHE:-$(pwd)}"
mkdir -p "$CACHE"

cache_get() {
    local location="$1"

    local name="${location##*/}"
    local entry="$CACHE/$name"
    local lock="$entry.lock"
    # entry exists already
    if [ -f "$entry" ]; then
        # and is not in the process of being created
        if [ ! -f "$lock" ]; then
            # so it's all good
            cp "$entry" .
            return 0
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
    curl -L -o "$tmp_slot" "$location" 2> "$lock"
    mv -f "$tmp_slot" "$entry"

    # got it, remove the lock so others can read it
    rm -f "$lock"
    cp "$entry" .

    # indicate freshness of the entry
    touch "$entry"

    return 0

}
