git submodule init

# Ensure that the submodules repository is absolutely pristine and unchanged. exit with 1 if changes have occured.
pushd chroma-externals
git reset --hard
git clean -dfx
popd

if ! git submodule update; then
    commit_message=$(git log -n 1)
    ext_rev=$(echo "$commit_message" | sed -ne '/^    chroma-externals:/s/^ *chroma-externals: *//p')
    if [ -z "$ext_rev" ]; then
        echo "chroma-externals reference is invalid and no chroma-externals: reference was specified in the commit message:
$commit_message
Aborting."
        exit 1
    fi
    change_num=${ext_rev%/*}
    revision_num=${ext_rev#*/}

    pushd chroma-externals
    if ! git fetch ssh://hudson@review.whamcloud.com:29418/chroma-externals refs/changes/${change_num: -2:2}/${change_num}/${revision_num}; then
        echo "$ext_rev is an invalid reference to chroma-externals.  Aborting."
        exit 1
    fi
    git checkout FETCH_HEAD
    popd
fi
