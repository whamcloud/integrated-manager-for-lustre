# REBOOT_NODE is used by other scripts that include this one
# shellcheck disable=SC2034
export REBOOT_NODE="sync
sync
nohup bash -c \"sleep 2; init 6\" >/dev/null 2>/dev/null </dev/null & exit 0"
