TEST_TIMEOUT = 5 * 60  # Timeout for waiting for a command to complete.
LONG_TEST_TIMEOUT = 3 * TEST_TIMEOUT  # An extra long timeout for a few particularly long activites, like creating a filesystem.
UNATTENDED_BOOT_TIMEOUT = 60
UPDATE_TEST_TIMEOUT = 3600  # An extra long timeout for updating storage servers. Since IML forces nodes in the same HA pair to update in serial, this needs to be 2x what it takes. Its also slower on RHEL, since then it connects to the external RHN repos.
INSTALL_TIMEOUT = 5400  # an extra long timeout for installing IML. Can take a while to install all those packages, and is lower on RHEL since then it connects to the external RHN repos. Storage server pairs being installed in serial makes 2x longer as well.
