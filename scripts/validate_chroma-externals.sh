
# Ensure that the submodules repository still absolutely pristine and unmodified.
# If any changes exist then exit with 1
pushd chroma-externals
files_changed=`git status --porcelain`
popd

if [ "$files_changed" != "" ];
then
    echo "chroma-externals was modified as part of the build making the build invalid"
    echo "Output of git status --porcelain is"
    echo $files_changed
    exit 1
fi
