SPECFILE := $(shell if [ -d "$(spec)" ]; then \
                        ls *.spec | head -1;  \
                    else                      \
                        echo "$(spec)";       \
                    fi)
ifeq ($(SPECFILE),)
$(error "SPECFILE cannot be empty!")
endif

srpm:
	dnf -y install 'dnf-command(copr)' rpmdevtools wget
	dnf -y --setopt=reposdir=/tmp/yum.repos.d copr enable clime/rpkg-client
	dnf -y install rpkg
	spectool -g $(SPECFILE)
	rpkg srpm --outdir=$(outdir) --spec=$(SPECFILE)
