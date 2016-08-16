TEST_TIMEOUT = 10 * 60  # Timeout for waiting for a command to complete.
LONG_TEST_TIMEOUT = 3 * TEST_TIMEOUT  # An extra long timeout for a few particularly long activites, like creating a filesystem.
UNATTENDED_BOOT_TIMEOUT = 60

# An extra long timeout for updating storage servers, it is long because the DKMS builds can take a long time.
# It's also slower on RHEL, since then it connects to the external RHN repos.
# As we increase the number of dkms packages this number will increase.
# It is also twice as long as we expect because we do HA pairs sequentially.
UPDATE_TEST_TIMEOUT = 7200
INSTALL_TIMEOUT = 5400  # an extra long timeout for installing IML. Can take a while to install all those packages, and is slower on RHEL since then it connects to the external RHN repos. Storage server pairs being installed in serial makes 2x longer as well.

MEGABYTES = (1024 * 1024)

# Return codes that could be returned by command() paramiko code, -1 is returned if no return code is
# recovered from channel.recv_exit_status(), 0-255 (unsigned byte) are return code values that could be returned
RETURN_CODES_ALL = tuple(range(-1, 256))
RETURN_CODES_SUCCESS = (0,)
RETURN_CODES_CHANNEL_FAIL = (-1,)
RETURN_CODES_GREP_NOT_FOUND = (1,)
