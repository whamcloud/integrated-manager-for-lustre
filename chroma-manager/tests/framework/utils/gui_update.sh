# Function returns true if the current change is a GUI bump. I.e. a GUI change.
function gui_bump() {
  files_changed=$(git diff-tree --no-commit-id --name-only -r HEAD)

  if [ "$files_changed" == "chroma-manager/ui-modules/package.json" ]; then
    true
  else
    false
  fi
}
